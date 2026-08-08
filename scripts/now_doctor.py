#!/usr/bin/env python3
"""Deterministic now/ health checker + auto-fixer — keeps the operational layer self-true.

THE POINT (companion to week_roll.py): the agent keeps `now/` honest by hand during work, and
`/sync` reconciles it richly. THIS is the bulletproof, no-LLM backstop — a pure-stdlib program
the laptop can run on a schedule that mechanically repairs the *mechanical* drift (a done issue
left in its area folder, an INDEX row whose status no longer matches the issue, a stale Completed
roster) and *flags* the judgement calls (duplicate ids, missing fields, broken links, stale `doing`).

Same house style as week_roll.py: stdlib-only (zero pip deps), git via subprocess, scoped commit +
push of only the paths it touched, idempotent (a second run with nothing to fix is a clean no-op).

The single source of truth is **per-issue frontmatter**. INDEX.md is a human view — when it disagrees
with an issue's frontmatter, the frontmatter wins (the auto-fixers rewrite INDEX, never the issue).

Checks (each yields findings; level = ok | fixed | flag):
  AUTO-FIX (safe, mechanical, idempotent):
    B  Done ⇒ right place — `status: done` files belong in completed/<closed-month>/; move + relink.
    C  INDEX active-row drift — status/priority/owner cells must equal frontmatter; rewrite the cells.
    D  Completed roster regen — rebuild the per-month roster lines from the actual completed/ folders.
  FLAG ONLY (judgement / unsafe to auto-edit):
    A  Integrity — duplicate ids; missing required field; reports max id (next-id).
    B2 a completed/ file whose status is not done/dropped (inconsistent).
    C2 an active issue with no INDEX row, or an INDEX row whose issue file is gone.
    E  STATE budget — STATE.md > 60 lines, or "Right now" has no resolvable first #id.
    F  Broken relative links — a markdown ](rel) or YAML `- rel` whose target doesn't resolve.
    G  Stale doing — `status: doing` with no git movement on the file in > 10 days.

Modes:
  (default)     run checks, APPLY auto-fixes, write now/HEALTH.md, then commit + push the changed
                now/ paths (one scoped commit; idempotent — no change ⇒ no commit).
  --check       checks only; report to stdout + HEALTH.md; exit 1 if any flags, 0 if clean. No fixes.
  --no-push     auto-fix + commit but don't push.
  --no-commit   auto-fix + write files but don't commit (used by tests / dry inspection).
  --now-dir P   override the now/ directory (default: the repo's now/ next to this script).

Usage:
  python3 scripts/now_doctor.py [--check] [--no-push] [--no-commit] [--now-dir PATH]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

# ── conventions ───────────────────────────────────────────────────────────────
AREAS = ("personal", "business", "tech")
REQUIRED_FIELDS = ("id", "title", "status", "area", "owner")
DONE_STATUSES = {"done", "dropped"}
ACTIVE_STATUSES = {"todo", "doing", "blocked", "review", "loop-queued", "loop-running"}
STALE_DOING_DAYS = 10
STATE_BUDGET_LINES = 60
SKIP_NAMES = {"INDEX.md", "README.md", "CONTRACT.md"}

ISSUE_ID_RE = re.compile(r"#(\d+)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Roster line, e.g.  - **2026-06** (19) → [`completed/2026-06/`](completed/2026-06/): #5 · #9 · …
ROSTER_LINE_RE = re.compile(r"^\s*-\s*\*\*(\d{4}-\d{2})\*\*", re.MULTILINE)


# ── finding model ─────────────────────────────────────────────────────────────
class Finding:
    """One observation. level ∈ {ok, fixed, flag}; check is the letter; msg is human text."""

    def __init__(self, check: str, level: str, msg: str):
        self.check = check
        self.level = level
        self.msg = msg


# ── frontmatter (stdlib only — no yaml dep, matching week_roll.py) ─────────────
def parse_frontmatter(text: str) -> tuple[dict, list[str]]:
    """Return (scalars, links). Scalars are simple `key: value` lines; links are the YAML
    list under a `links:` key (the only block we need). Mirrors week_roll._frontmatter but also
    captures the links list, because the link-recompute + check F need it."""
    scalars: dict[str, str] = {}
    links: list[str] = []
    if not text.startswith("---"):
        return scalars, links
    end = text.find("\n---", 3)
    if end == -1:
        return scalars, links
    body = text[3:end]
    in_links = False
    for line in body.splitlines():
        if re.match(r"^\s*-\s+", line) and in_links:
            links.append(line.split("-", 1)[1].strip())
            continue
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            in_links = key == "links"
            if not in_links:
                scalars[key] = val
        else:
            in_links = False
    return scalars, links


# ── issue model ───────────────────────────────────────────────────────────────
class Issue:
    def __init__(self, path: Path, fm: dict, links: list[str]):
        self.path = path
        self.fm = fm
        self.links = links
        try:
            self.id = int(fm["id"]) if "id" in fm and fm["id"] != "" else None
        except (ValueError, TypeError):
            self.id = None
        self.status = (fm.get("status") or "").strip().lower()
        self.priority = (fm.get("priority") or "").strip().upper()
        self.owner = (fm.get("owner") or "").strip().lower()
        self.area = (fm.get("area") or "").strip().lower()
        self.title = (fm.get("title") or "").strip()
        self.closed = (fm.get("closed") or "").strip()
        self.intent = (fm.get("intent") or "").strip()
        self.due = (fm.get("due") or "").strip()

    @property
    def in_completed(self) -> bool:
        return "completed" in self.path.parts

    def completed_month(self) -> str | None:
        """The completed/<YYYY-MM>/ bucket name from the path, if any."""
        parts = self.path.parts
        if "completed" in parts:
            i = parts.index("completed")
            if i + 1 < len(parts) and re.fullmatch(r"\d{4}-\d{2}", parts[i + 1]):
                return parts[i + 1]
        return None


def load_issues(now_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    issues_dir = now_dir / "issues"
    for p in sorted(issues_dir.rglob("*.md")):
        if p.name.startswith("_TEMPLATE") or p.name in SKIP_NAMES:
            continue
        fm, links = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        if "id" not in fm:
            continue
        issues.append(Issue(p, fm, links))
    return issues


# ── link recompute (robust, depth-agnostic) ──────────────────────────────────
def _is_external(rel: str) -> bool:
    rel = rel.strip()
    if not rel:
        return True
    # http/mailto/anchor/abs-path; also `~`-home paths and `<placeholder>` template text — none
    # are resolvable relative links, so they're not "broken", they're just not ours to check.
    if rel.startswith(("http://", "https://", "mailto:", "#", "/", "~", "<")):
        return True
    return False


def _resolve_core(rel: str) -> str | None:
    """The filesystem-resolvable core of a link target, or None if it's external/placeholder.
    Strips a trailing inline ` # comment` (real in some YAML `links:` entries) and a `#anchor`,
    then URL-decodes (`%20` → space) so `PRD%20Docs/…` and `PRD Docs/…` both resolve on disk."""
    rel = rel.strip()
    if _is_external(rel):
        return None
    rel = re.split(r"\s+#", rel, maxsplit=1)[0].strip()  # drop a trailing inline comment
    core = rel.split("#", 1)[0].strip()                  # drop a markdown #anchor
    if not core:
        return None
    return unquote(core)


def _anchor_of(rel: str) -> str:
    body = re.split(r"\s+#", rel.strip(), maxsplit=1)[0]
    return ("#" + body.split("#", 1)[1]) if "#" in body else ""


def recompute_links(text: str, old_path: Path, new_path: Path) -> str:
    """Rewrite every *relative* link target for a file moving old_path → new_path.

    For each relative target `rel` (markdown `](rel)` and YAML list `- rel`):
      target = normpath(dirname(old_path)/rel)
      if target exists on disk → new_rel = relpath(target, dirname(new_path)); substitute.
      else (already-broken) → leave as-is (it'll surface in check F).
    Handles any change in directory depth correctly (not a +1 hack)."""
    old_dir = old_path.parent
    new_dir = new_path.parent

    def _remap(rel: str) -> str | None:
        core = _resolve_core(rel)
        if core is None:
            return None
        norm = Path(os.path.normpath(str(old_dir / core)))
        if not norm.exists():
            return None  # already broken → leave for check F
        # Re-encode spaces as %20 on output (matches the file convention) + keep any #anchor.
        new_rel = os.path.relpath(str(norm), str(new_dir)).replace(" ", "%20")
        return new_rel + _anchor_of(rel)

    # Markdown ](rel)
    def _md_sub(m: re.Match) -> str:
        rel = m.group(1)
        out = _remap(rel)
        return f"]({out})" if out is not None else m.group(0)

    text = re.sub(r"\]\(([^)]+)\)", _md_sub, text)

    # YAML list links under frontmatter: lines like `  - ../../foo.md`
    out_lines = []
    in_fm = text.startswith("---")
    fm_end_seen = False
    in_links = False
    for i, line in enumerate(text.splitlines(keepends=False)):
        if in_fm and not fm_end_seen:
            if i > 0 and line.strip() == "---":
                fm_end_seen = True
                out_lines.append(line)
                continue
            mk = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
            if mk:
                in_links = mk.group(1) == "links"
                out_lines.append(line)
                continue
            ml = re.match(r"^(\s*-\s+)(\S.*)$", line)
            if ml and in_links:
                rel = ml.group(2).strip()
                out = _remap(rel)
                out_lines.append(f"{ml.group(1)}{out}" if out is not None else line)
                continue
            out_lines.append(line)
        else:
            out_lines.append(line)
    # Preserve a trailing newline if the original had one.
    result = "\n".join(out_lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def collect_relative_links(text: str) -> list[str]:
    """Every relative link target in a file (markdown ](rel) + YAML `- rel` under links:)."""
    out: list[str] = []
    for m in re.finditer(r"\]\(([^)]+)\)", text):
        rel = m.group(1)
        if not _is_external(rel.split("#", 1)[0]):
            out.append(rel.split("#", 1)[0])
    # YAML links list
    fm, links = parse_frontmatter(text)
    for rel in links:
        if not _is_external(rel):
            out.append(rel)
    return out


# ── git helpers (copied pattern from week_roll.py) ────────────────────────────
def _repo_root(now_dir: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(now_dir), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    ).stdout.strip()


def git(now_dir: Path, *args: str) -> subprocess.CompletedProcess:
    root = _repo_root(now_dir)
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


def last_commit_iso(now_dir: Path, path: Path) -> str | None:
    """`git log -1 --format=%cI -- <path>` → the file's last-commit ISO datetime, or None."""
    root = _repo_root(now_dir)
    if not root:
        return None
    try:
        rel = os.path.relpath(str(path), root)
    except ValueError:
        rel = str(path)
    r = subprocess.run(
        ["git", "-C", root, "log", "-1", "--format=%cI", "--", rel],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    return out or None


# ── INDEX row helpers ─────────────────────────────────────────────────────────
def index_active_rows(index_text: str) -> dict[int, tuple[int, str]]:
    """Map id → (line_index, line_text) for every active table row in INDEX.md.
    A row looks like: | [<id>](<area>/<file>) | <title> | <status> | <pri> | <owner> | <due> | <intent> |"""
    rows: dict[int, tuple[int, str]] = {}
    for i, line in enumerate(index_text.splitlines()):
        m = re.match(r"^\|\s*\[(\d+)\]\([^)]+\)\s*\|", line)
        if m:
            rows[int(m.group(1))] = (i, line)
    return rows


def rewrite_row_cells(line: str, status: str, priority: str, owner: str) -> str:
    """Rewrite cells 3 (status), 4 (priority), 5 (owner) of a 7-cell INDEX row, preserving the
    rest (id-link, title, due, intent) and the owner's bold convention (**me** vs agent)."""
    # Split on '|' — leading/trailing empties from the bordering pipes.
    cells = line.split("|")
    # cells[0] = '' (before first |); cells[1]=id-link, [2]=title, [3]=status, [4]=pri,
    # [5]=owner, [6]=due, [7]=intent, [8]='' (after last |)
    if len(cells) < 8:
        return line  # malformed — leave it (won't happen for well-formed rows)
    owner_disp = f" **{owner}** " if owner and owner != "agent" else f" {owner} "
    cells[3] = f" {status} "
    cells[4] = f" {priority} "
    cells[5] = owner_disp
    return "|".join(cells)


# ── the checks ────────────────────────────────────────────────────────────────
def check_A_integrity(issues: list[Issue]) -> list[Finding]:
    findings: list[Finding] = []
    seen: dict[int, Path] = {}
    max_id = 0
    for iss in issues:
        # missing required field
        missing = [f for f in REQUIRED_FIELDS if not (iss.fm.get(f) or "").strip()]
        if missing:
            findings.append(Finding("A", "flag",
                f"{iss.path.name}: missing required field(s): {', '.join(missing)}."))
        if iss.id is None:
            continue
        max_id = max(max_id, iss.id)
        if iss.id in seen:
            findings.append(Finding("A", "flag",
                f"duplicate id #{iss.id}: {seen[iss.id].name} and {iss.path.name}."))
        else:
            seen[iss.id] = iss.path
    findings.append(Finding("A", "ok", f"max id = {max_id} (next id = {max_id + 1})."))
    return findings


def check_B_done_placement(now_dir: Path, issues: list[Issue], apply: bool) -> tuple[list[Finding], set[str], dict[Path, Path]]:
    """Done ⇒ must live in completed/<closed-month>/. Move + relink misplaced done issues.
    Returns (findings, touched_relpaths, moved{old:new})."""
    findings: list[Finding] = []
    touched: set[str] = set()
    moved: dict[Path, Path] = {}
    issues_dir = now_dir / "issues"
    repo_rel_base = now_dir.name  # 'now'
    for iss in issues:
        if iss.status not in DONE_STATUSES:  # done OR dropped — both are terminal (off the board)
            continue
        # Terminal home: `done` → completed/<closed-month>/ (the archive, by month);
        # `dropped` ("won't do") → dropped/ (a flat shelf, same depth as the area folders).
        if iss.status == "dropped":
            want_dir = issues_dir / "dropped"
            already_right = "dropped" in iss.path.parts
            dest_desc = "dropped/"
        else:
            if not (iss.closed and DATE_RE.match(iss.closed)):
                findings.append(Finding("B", "flag",
                    f"#{iss.id} {iss.path.name}: status done but `closed:` is missing/invalid "
                    f"({iss.closed!r}) — can't pick a month bucket. Fill closed: then re-run."))
                continue
            month = iss.closed[:7]  # YYYY-MM
            want_dir = issues_dir / "completed" / month
            already_right = iss.in_completed and iss.completed_month() == month
            dest_desc = f"completed/{month}/"
        if already_right:
            continue
        new_path = want_dir / iss.path.name
        if not apply:
            findings.append(Finding("B", "flag",
                f"#{iss.id} {iss.path.name}: {iss.status} → should move to {dest_desc} "
                f"(currently {iss.path.relative_to(now_dir)})."))
            continue
        # Apply the move + relink.
        want_dir.mkdir(parents=True, exist_ok=True)
        text = iss.path.read_text(encoding="utf-8")
        new_text = recompute_links(text, iss.path, new_path)
        new_path.write_text(new_text, encoding="utf-8")
        if new_path != iss.path:
            iss.path.unlink()
        moved[iss.path] = new_path
        # update the issue's in-memory path so later checks see the new location
        old_path = iss.path
        iss.path = new_path
        findings.append(Finding("B", "fixed",
            f"#{iss.id} moved {old_path.relative_to(now_dir)} → "
            f"{new_path.relative_to(now_dir)} (links recomputed)."))
        touched.add(f"{repo_rel_base}/{old_path.relative_to(now_dir)}")
        touched.add(f"{repo_rel_base}/{new_path.relative_to(now_dir)}")
    return findings, touched, moved


def check_B2_completed_consistency(now_dir: Path, issues: list[Issue]) -> list[Finding]:
    findings: list[Finding] = []
    for iss in issues:
        if iss.in_completed and iss.status != "done":
            findings.append(Finding("B2", "flag",
                f"#{iss.id} {iss.path.name}: lives in completed/ but status is "
                f"`{iss.status}` (expected done)."))
        if "dropped" in iss.path.parts and iss.status != "dropped":
            findings.append(Finding("B2", "flag",
                f"#{iss.id} {iss.path.name}: lives in dropped/ but status is "
                f"`{iss.status}` (expected dropped)."))
    return findings


def check_C_index_rows(now_dir: Path, issues: list[Issue], apply: bool) -> tuple[list[Finding], set[str]]:
    """Active-row drift: status/priority/owner cells must equal frontmatter; rewrite the cells.
    Also C2: active issue with no row / row with no issue file."""
    findings: list[Finding] = []
    touched: set[str] = set()
    index_path = now_dir / "issues" / "INDEX.md"
    if not index_path.exists():
        findings.append(Finding("C", "flag", "INDEX.md not found."))
        return findings, touched
    text = index_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows = index_active_rows(text)
    active = {iss.id: iss for iss in issues if iss.id is not None and not iss.in_completed
              and iss.status not in DONE_STATUSES}

    changed = False
    for iid, iss in sorted(active.items()):
        if iid not in rows:
            findings.append(Finding("C2", "flag",
                f"#{iid} {iss.path.name}: active issue has no INDEX row."))
            continue
        line_i, line = rows[iid]
        cells = line.split("|")
        if len(cells) < 8:
            continue
        cur_status = cells[3].strip()
        cur_pri = cells[4].strip()
        cur_owner = cells[5].replace("*", "").strip()
        drift = []
        if cur_status.lower() != iss.status:
            drift.append(f"status {cur_status!r}→{iss.status!r}")
        if cur_pri.upper() != iss.priority:
            drift.append(f"pri {cur_pri!r}→{iss.priority!r}")
        if cur_owner.lower() != iss.owner:
            drift.append(f"owner {cur_owner!r}→{iss.owner!r}")
        if not drift:
            continue
        if not apply:
            findings.append(Finding("C", "flag",
                f"#{iid} INDEX row drift: {', '.join(drift)}."))
            continue
        lines[line_i] = rewrite_row_cells(line, iss.status, iss.priority, iss.owner)
        changed = True
        findings.append(Finding("C", "fixed",
            f"#{iid} INDEX row cells synced to frontmatter ({', '.join(drift)})."))

    # C2: rows whose issue file is gone (or now done/moved-out)
    for iid, (line_i, line) in sorted(rows.items()):
        if iid not in active:
            # Is it a known done/completed issue? then it's a roster concern, not C2.
            known = next((i for i in issues if i.id == iid), None)
            if known is None:
                findings.append(Finding("C2", "flag",
                    f"#{iid}: INDEX active row references an issue with no matching file."))
            elif known.status in DONE_STATUSES or known.in_completed:
                findings.append(Finding("C2", "flag",
                    f"#{iid}: still in an INDEX active table but it is "
                    f"`{known.status}`/completed — remove the row (add to the roster)."))

    if apply and changed:
        new_text = "\n".join(lines)
        if text.endswith("\n"):
            new_text += "\n"
        index_path.write_text(new_text, encoding="utf-8")
        touched.add(f"{now_dir.name}/issues/INDEX.md")
    return findings, touched


def build_roster_lines(now_dir: Path) -> list[str]:
    """Build the per-month roster from the actual completed/<YYYY-MM>/ folders.
    One line per month, NEWEST MONTH LAST (chronological — matches the existing file + git/week
    conventions where time runs forward down the page)."""
    completed = now_dir / "issues" / "completed"
    lines: list[str] = []
    if not completed.exists():
        return lines
    months = sorted(d.name for d in completed.iterdir()
                    if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}", d.name))
    for month in months:  # ascending → newest last
        mdir = completed / month
        ids: list[int] = []
        for p in mdir.glob("*.md"):
            if p.name.startswith("_TEMPLATE") or p.name in SKIP_NAMES:
                continue
            fm, _ = parse_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
            if "id" in fm:
                try:
                    ids.append(int(fm["id"]))
                except ValueError:
                    pass
        ids.sort()
        ids_str = " · ".join(f"#{i}" for i in ids)
        lines.append(
            f"- **{month}** ({len(ids)}) → [`completed/{month}/`](completed/{month}/): {ids_str}"
        )
    return lines


def check_D_roster(now_dir: Path, apply: bool) -> tuple[list[Finding], set[str]]:
    """Regenerate the per-month roster block in INDEX.md between the `## ✅ Completed` heading
    and the next `##`."""
    findings: list[Finding] = []
    touched: set[str] = set()
    index_path = now_dir / "issues" / "INDEX.md"
    if not index_path.exists():
        return findings, touched
    text = index_path.read_text(encoding="utf-8")
    want_lines = build_roster_lines(now_dir)

    # Find the Completed heading (matches `## ✅ Completed...` or `## Completed...`).
    head_m = re.search(r"^##[ \t]+(?:✅[ \t]*)?Completed.*$", text, re.MULTILINE)
    if not head_m:
        findings.append(Finding("D", "flag",
            "INDEX.md has no `## Completed` heading — can't place the roster."))
        return findings, touched
    after_head = head_m.end()
    # Next heading of level ## or higher after the Completed heading.
    next_m = re.search(r"^##[ \t]", text[after_head:], re.MULTILINE)
    section_end = after_head + next_m.start() if next_m else len(text)
    section = text[after_head:section_end]

    # Existing roster lines (the `- **YYYY-MM**...` bullets) in that section.
    existing = [l for l in section.splitlines() if ROSTER_LINE_RE.match(l)]
    if existing == want_lines:
        findings.append(Finding("D", "ok", f"Completed roster current ({len(want_lines)} month(s))."))
        return findings, touched

    if not apply:
        findings.append(Finding("D", "flag",
            f"Completed roster drift — {len(existing)} line(s) on file vs "
            f"{len(want_lines)} from folders."))
        return findings, touched

    # Rebuild the section: keep any leading prose (the explainer paragraph), replace the
    # contiguous roster bullets at the end with the regenerated set.
    sec_lines = section.splitlines()
    # Drop existing roster bullets; keep everything else (prose). Then append fresh roster.
    kept = [l for l in sec_lines if not ROSTER_LINE_RE.match(l)]
    # Trim trailing blank lines from kept, then add one blank + the roster.
    while kept and kept[-1].strip() == "":
        kept.pop()
    new_section_lines = kept + [""] + want_lines
    new_section = "\n".join(new_section_lines)
    # Preserve the section's leading newline (head_m.end() sits right after the heading text).
    lead = ""
    if section.startswith("\n"):
        lead = "\n"
        new_section = "\n" + new_section
    new_text = text[:after_head] + new_section + ("\n" if not new_section.endswith("\n") else "") + text[section_end:]
    # Avoid double blank lines at the seam.
    new_text = re.sub(r"\n{3,}", "\n\n", new_text)
    index_path.write_text(new_text, encoding="utf-8")
    touched.add(f"{now_dir.name}/issues/INDEX.md")
    findings.append(Finding("D", "fixed",
        f"Completed roster regenerated ({len(want_lines)} month line(s)) from folders."))
    return findings, touched


def check_E_state_budget(now_dir: Path, issues: list[Issue]) -> list[Finding]:
    findings: list[Finding] = []
    state_path = now_dir / "STATE.md"
    if not state_path.exists():
        findings.append(Finding("E", "flag", "STATE.md not found."))
        return findings
    text = state_path.read_text(encoding="utf-8")
    n = len(text.splitlines())
    if n > STATE_BUDGET_LINES:
        findings.append(Finding("E", "flag",
            f"STATE.md is {n} lines (budget ≤ {STATE_BUDGET_LINES}) — trim it."))
    # "Right now" first #id must resolve to a known issue.
    m = re.search(r"##\s*Right now.*?(?=\n##\s|\Z)", text, re.DOTALL | re.IGNORECASE)
    known_ids = {iss.id for iss in issues if iss.id is not None}
    if not m:
        findings.append(Finding("E", "flag",
            "STATE.md has no `## Right now` section — the app's hero resolves its first #id."))
    else:
        ids = ISSUE_ID_RE.findall(m.group(0))
        if not ids:
            findings.append(Finding("E", "flag",
                "STATE.md `## Right now` has no #id — the app's hero card can't resolve a focus issue."))
        elif int(ids[0]) not in known_ids:
            findings.append(Finding("E", "flag",
                f"STATE.md `## Right now` first #id is #{ids[0]} but no such issue exists."))
    return findings


def check_F_links(now_dir: Path, issues: list[Issue], apply: bool) -> tuple[list[Finding], set[str]]:
    """Every relative link in every now/ markdown file must resolve.
    AUTO-FIX a broken link whose target is an issue file `<id>-slug.md` by relinking it to that
    issue's CURRENT path (the id is unambiguous → safe). Everything else (a missing PRD/studio doc,
    a renamed file) is FLAGGED for a human / `/sync` — never guessed."""
    findings: list[Finding] = []
    touched: set[str] = set()
    by_id = {iss.id: iss.path for iss in issues if iss.id is not None}
    for p in sorted(now_dir.rglob("*.md")):
        if p.name == "HEALTH.md":  # generated report — not a source doc
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        new_text = text
        for rel in collect_relative_links(text):
            core = _resolve_core(rel)
            if core is None:
                continue
            if Path(os.path.normpath(str(p.parent / core))).exists():
                continue  # resolves — fine
            mb = re.match(r"(\d+)-", os.path.basename(core))
            iid = int(mb.group(1)) if mb else None
            if iid is not None and iid in by_id and by_id[iid].resolve() != p.resolve():
                want = os.path.relpath(str(by_id[iid]), str(p.parent)).replace(" ", "%20")
                if apply:
                    new_text = new_text.replace(f"]({rel})", f"]({want})").replace(f"- {rel}", f"- {want}")
                    findings.append(Finding("F", "fixed",
                        f"{p.relative_to(now_dir)}: relinked broken issue ref → #{iid} ({want})."))
                else:
                    findings.append(Finding("F", "flag",
                        f"{p.relative_to(now_dir)}: broken issue link `{rel}` (auto-fixable → #{iid})."))
            else:
                findings.append(Finding("F", "flag",
                    f"{p.relative_to(now_dir)}: broken relative link → `{rel}`."))
        if apply and new_text != text:
            p.write_text(new_text, encoding="utf-8")
            touched.add(f"{now_dir.name}/{p.relative_to(now_dir)}")
    return findings, touched


def check_G_stale_doing(now_dir: Path, issues: list[Issue]) -> list[Finding]:
    findings: list[Finding] = []
    now_dt = datetime.now(timezone.utc)
    for iss in issues:
        if iss.status != "doing":
            continue
        iso = last_commit_iso(now_dir, iss.path)
        if not iso:
            continue  # untracked / never committed — not "stale", just new
        try:
            when = datetime.fromisoformat(iso)
        except ValueError:
            continue
        age = (now_dt - when).days
        if age > STALE_DOING_DAYS:
            findings.append(Finding("G", "flag",
                f"#{iss.id} {iss.path.name}: status `doing` but no git movement in "
                f"{age} days (> {STALE_DOING_DAYS}) — finish, re-slate, or drop."))
    return findings


# ── report ────────────────────────────────────────────────────────────────────
def render_report(findings: list[Finding], stamp: str) -> str:
    fixed = [f for f in findings if f.level == "fixed"]
    flags = [f for f in findings if f.level == "flag"]
    oks = [f for f in findings if f.level == "ok"]
    lines = [
        "# now/ health — generated by now_doctor.py",
        "",
        f"> Run: {stamp}. Deterministic, stdlib-only. **Do not hand-edit** — overwritten each run.",
        "",
        "## ✅ Summary",
        f"- Auto-fixed: **{len(fixed)}**",
        f"- Needs attention (flags): **{len(flags)}**",
    ]
    for f in oks:
        lines.append(f"- {f.msg}")
    lines.append("")
    lines.append("## 🔧 Auto-fixed")
    if fixed:
        for f in fixed:
            lines.append(f"- [{f.check}] {f.msg}")
    else:
        lines.append("- _(nothing to fix — clean)_")
    lines.append("")
    lines.append("## ⚠️ Needs attention")
    if flags:
        for f in flags:
            lines.append(f"- [{f.check}] {f.msg}")
    else:
        lines.append("- _(no flags — all green)_")
    lines.append("")
    return "\n".join(lines)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


# ── orchestration ─────────────────────────────────────────────────────────────
def run(now_dir: Path, apply: bool) -> tuple[list[Finding], set[str]]:
    """Run all checks. If apply, perform the auto-fixes. Returns (findings, touched_relpaths)."""
    issues = load_issues(now_dir)
    findings: list[Finding] = []
    touched: set[str] = set()

    findings += check_A_integrity(issues)

    fB, tB, _moved = check_B_done_placement(now_dir, issues, apply)
    findings += fB
    touched |= tB

    findings += check_B2_completed_consistency(now_dir, issues)

    # Re-load after moves so INDEX/roster checks see the post-move tree.
    if apply and tB:
        issues = load_issues(now_dir)

    fC, tC = check_C_index_rows(now_dir, issues, apply)
    findings += fC
    touched |= tC

    fD, tD = check_D_roster(now_dir, apply)
    findings += fD
    touched |= tD

    findings += check_E_state_budget(now_dir, issues)
    fF, tF = check_F_links(now_dir, issues, apply)
    findings += fF
    touched |= tF
    findings += check_G_stale_doing(now_dir, issues)

    return findings, touched


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic now/ health checker + auto-fixer.")
    default_now = Path(__file__).resolve().parent.parent / "now"
    ap.add_argument("--now-dir", default=str(default_now), help="override the now/ directory")
    ap.add_argument("--check", action="store_true",
                    help="checks only; report to stdout + HEALTH.md; exit 1 if any flags. No fixes.")
    ap.add_argument("--no-push", action="store_true", help="auto-fix + commit but don't push")
    ap.add_argument("--no-commit", action="store_true",
                    help="auto-fix + write files but don't commit (tests / dry inspection)")
    args = ap.parse_args()

    now_dir = Path(args.now_dir).expanduser().resolve()
    if not now_dir.exists():
        print(f"now-dir not found: {now_dir}", file=sys.stderr)
        return 2

    apply = not args.check
    findings, touched = run(now_dir, apply=apply)
    stamp = utc_stamp()
    report = render_report(findings, stamp)

    # Always write HEALTH.md (overwrite, bounded).
    health = now_dir / "HEALTH.md"
    health.write_text(report, encoding="utf-8")
    flags = [f for f in findings if f.level == "flag"]
    fixed = [f for f in findings if f.level == "fixed"]

    if args.check:
        print(report)
        return 1 if flags else 0

    # default / --no-push / --no-commit path. HEALTH.md is gitignored (a generated, always-current
    # report on disk) and is NOT committed — so the doctor only commits real mechanical fixes, and a
    # clean run is a true no-op (no daily HEALTH.md-churn commit on the schedule).
    summary = f"{len(fixed)} fixed, {len(flags)} flags"
    print(report)
    print(f"\n[now-doctor] {summary}")

    if args.no_commit:
        print("[now-doctor] --no-commit: wrote files, no commit.")
        return 0

    if not touched:
        print("[now-doctor] no mechanical fixes — nothing to commit (HEALTH.md refreshed on disk).")
        return 0

    paths = sorted(touched)
    git(now_dir, "add", "--", *paths)
    msg = f"now-doctor: {summary}"
    c = git(now_dir, "commit", "-m", msg, "--", *paths)
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print(f"[now-doctor] commit failed: {c.stderr.strip()}", file=sys.stderr)
        return 1
    print(f"[now-doctor] committed: {msg}")
    if not args.no_push:
        p = git(now_dir, "push")
        print("[now-doctor] pushed." if p.returncode == 0
              else f"[now-doctor] push failed (safe locally): {p.stderr.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
