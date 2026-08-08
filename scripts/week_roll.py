#!/usr/bin/env python3
"""Deterministic week-roll — keeps the now/ operational layer alive with zero human input.

THE POINT (vacation-proof): the agent `/week-roll` command is the rich, interactive roll.
THIS is the bulletproof backstop — a pure-stdlib, no-LLM, no-network-but-git program that the
laptop runs on a schedule (launchd, every Monday). Even if the owner never opens a session
for weeks, the week chain stays unbroken and the record is pushed to the git remote.

Bulletproof properties:
  • Deterministic — no LLM, no API keys, only python3 stdlib + git. Runs the same forever.
  • Catch-up — if it hasn't run for N weeks, it rolls ALL N weeks in one pass (loops to the
    current ISO week). Sleep/await-on-vacation can't break the chain.
  • Durable — commits the now/ changes AND `git push`es (when a remote is configured), so the
    record survives even if the laptop later dies.
  • Idempotent — if the current week's file already exists, it's a clean no-op.
  • Safe — only ever writes under now/ (week files + STATE pointer); never deletes; --dry-run
    prints the plan and writes nothing.

What each roll does, purely from data:
  • Closes the just-ended week file: fills **Shipped** (issues now in now/issues/completed/
    whose `closed:` falls in that week) and **Slipped / carried →** (its in-play `#ids` still
    open), appends a roll note.
  • Opens the next week's file from the template: carries the still-open in-play issues, seeds
    Focus from the closing week's "Next week" text (or the open P0/P1s), sets the Mon–Sun range.
  • Repoints STATE.md's "This week →" + "Last updated".

Usage:
  python3 scripts/week_roll.py [--dry-run] [--no-push] [--now-dir PATH] [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

WEEK_RE = re.compile(r"(\d{4})-W(\d{2})")
ISSUE_ID_RE = re.compile(r"#(\d+)")
_OPEN = {"todo", "doing", "blocked", "review"}


# ── ISO-week helpers ──────────────────────────────────────────────────────────
def week_id(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def week_monday(wid: str) -> date:
    m = WEEK_RE.search(wid)
    return date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)


def week_range_label(wid: str) -> str:
    mon = week_monday(wid)
    sun = mon + timedelta(days=6)
    return f"{mon.strftime('%b %-d')} – {sun.strftime('%b %-d')}"


def next_week_id(wid: str) -> str:
    return week_id(week_monday(wid) + timedelta(days=7))


# ── frontmatter (stdlib only — no yaml dependency, so the launchd job has zero deps) ──
def _frontmatter(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end == -1:
        return out
    for line in text[3:end].splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def load_issues(now_dir: Path) -> dict[int, dict]:
    """{id: {status, title, closed, area, path, completed:bool}} for every issue file."""
    issues: dict[int, dict] = {}
    for p in (now_dir / "issues").rglob("*.md"):
        if p.name.startswith("_TEMPLATE") or p.name in ("INDEX.md", "README.md", "CONTRACT.md"):
            continue
        fm = _frontmatter(p.read_text(encoding="utf-8", errors="replace"))
        if "id" not in fm:
            continue
        try:
            iid = int(fm["id"])
        except ValueError:
            continue
        issues[iid] = {
            "status": (fm.get("status") or "").strip().lower(),
            "title": (fm.get("title") or "").strip(),
            "closed": (fm.get("closed") or "").strip(),
            "priority": (fm.get("priority") or "").strip().upper(),
            "completed": "completed" in p.parts,
        }
    return issues


def in_week(closed: str, wid: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", closed or ""):
        return False
    try:
        d = date.fromisoformat(closed)
    except ValueError:
        return False
    return week_id(d) == wid


# ── the roll ──────────────────────────────────────────────────────────────────
def latest_existing_week(weeks_dir: Path) -> str | None:
    ids = sorted(WEEK_RE.search(p.name).group(0) for p in weeks_dir.glob("*.md") if WEEK_RE.search(p.name))
    return ids[-1] if ids else None


def in_play_ids(week_text: str) -> list[int]:
    """The #ids referenced under the week's '## In play' section."""
    m = re.search(r"##\s*In play.*?(?=\n##\s|\Z)", week_text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    seen, out = set(), []
    for mid in ISSUE_ID_RE.findall(m.group(0)):
        i = int(mid)
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def next_week_text(week_text: str) -> str:
    m = re.search(r"##\s*Next week\s*\n(.*?)(?=\n##\s|\Z)", week_text, re.DOTALL | re.IGNORECASE)
    return (m.group(1).strip() if m else "").strip()


def close_week_file(path: Path, wid: str, issues: dict[int, dict]) -> tuple[list[int], list[int]]:
    """Append Shipped + Slipped/carried to the closing week file (deterministic, from data).
    Returns (shipped_ids, carried_ids)."""
    text = path.read_text(encoding="utf-8") if path.exists() else f"# Week {wid} ({week_range_label(wid)})\n"
    shipped = sorted(i for i, v in issues.items() if v["completed"] and in_week(v["closed"], wid))
    carried = [i for i in in_play_ids(text) if i in issues and issues[i]["status"] in _OPEN]

    def _block(title: str, ids: list[int], how) -> str:
        if not ids:
            return ""
        lines = "\n".join(how(i) for i in ids)
        return f"\n{title}\n{lines}\n"

    note = (
        f"\n## Notes / log\n- {date.today().isoformat()}: week auto-rolled by week_roll.py → {next_week_id(wid)} "
        f"({len(shipped)} shipped · {len(carried)} carried).\n"
    )
    # Append a deterministic "(auto)" record — never clobber hand-written sections.
    text = text.rstrip() + "\n"
    text += _block(
        "## Shipped ✅ (auto)",
        shipped,
        lambda i: f"- #{i} {issues[i]['title']} — closed {issues[i]['closed']}.",
    )
    text += _block(
        "## Slipped / carried → (auto)",
        carried,
        lambda i: f"- #{i} {issues[i]['title']} ({issues[i]['status']}) — carried to {next_week_id(wid)}.",
    )
    text += note
    path.write_text(text, encoding="utf-8")
    return shipped, carried


def open_week_file(weeks_dir: Path, wid: str, prior_text: str, carried: list[int], issues: dict[int, dict]) -> Path:
    path = weeks_dir / f"{wid}.md"
    if path.exists():
        return path  # idempotent
    focus = next_week_text(prior_text)
    if not focus:
        p01 = sorted(i for i, v in issues.items() if v["status"] in _OPEN and v["priority"] in ("P0", "P1"))
        focus = "- " + (", ".join(f"#{i}" for i in p01[:8]) if p01 else "set the week's focus")
    in_play = "\n".join(
        f"- #{i} {issues[i]['title']} ({issues[i]['status']}) — carried." for i in carried
    ) or "- _(carry-over: none open)_"
    body = (
        f"# Week {wid} ({week_range_label(wid)})\n\n"
        f"**Focus:** _(auto-seeded — refine)_\n{focus}\n\n"
        f"**Serves intent(s):** _(set)_\n\n"
        f"## In play (issues)\n{in_play}\n\n"
        f"## Shipped ✅\n- _(none yet)_\n\n"
        f"## Slipped / carried →\n- _(none yet)_\n\n"
        f"## Notes / log\n- {date.today().isoformat()}: week opened by week_roll.py (auto).\n\n"
        f"## Next week\n- _(carry forward)_\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def repoint_state(now_dir: Path, current: str) -> None:
    sp = now_dir / "STATE.md"
    if not sp.exists():
        return
    t = sp.read_text(encoding="utf-8")
    t = re.sub(r"(\*\*Last updated:\*\*\s*)\d{4}-\d{2}-\d{2}", rf"\g<1>{date.today().isoformat()}", t, count=1)
    # Repoint any "weeks/<id>.md" reference in the "This week" pointer to the current week.
    t = re.sub(r"weeks/\d{4}-W\d{2}\.md", f"weeks/{current}.md", t)
    sp.write_text(t, encoding="utf-8")


def git(now_dir: Path, *args: str) -> subprocess.CompletedProcess:
    root = subprocess.run(
        ["git", "-C", str(now_dir), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    ).stdout.strip()
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Deterministic, vacation-proof week-roll for now/.")
    ap.add_argument("--now-dir", default=str(Path(__file__).resolve().parent.parent / "now"))
    ap.add_argument("--today", default=None, help="override today (YYYY-MM-DD) — for testing")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; write + commit nothing")
    ap.add_argument("--no-push", action="store_true", help="commit locally but do not push")
    args = ap.parse_args()

    now_dir = Path(args.now_dir).expanduser()
    today = date.fromisoformat(args.today) if args.today else date.today()
    weeks_dir = now_dir / "weeks"
    current = week_id(today)
    latest = latest_existing_week(weeks_dir)

    if latest is None:
        print("No week files found — nothing to roll from.")
        return 0
    if latest >= current:
        print(f"Up to date: latest week {latest} ≥ current {current}. No-op.")
        return 0

    issues = load_issues(now_dir)
    rolled: list[str] = []
    # Only ever stage/commit the files THIS roll touches — never `git add now/` (that would
    # sweep up the user's unrelated pending nudges). Paths are repo-root-relative.
    rel_now = now_dir.name  # 'now'
    touched: set[str] = set()
    wid = latest
    while wid < current:
        nxt = next_week_id(wid)
        if args.dry_run:
            text = (weeks_dir / f"{wid}.md").read_text(encoding="utf-8") if (weeks_dir / f"{wid}.md").exists() else ""
            shipped = sorted(i for i, v in issues.items() if v["completed"] and in_week(v["closed"], wid))
            carried = [i for i in in_play_ids(text) if i in issues and issues[i]["status"] in _OPEN]
            print(f"[dry-run] close {wid}: shipped={shipped} carried={carried} → open {nxt}")
        else:
            prior_text = (weeks_dir / f"{wid}.md").read_text(encoding="utf-8") if (weeks_dir / f"{wid}.md").exists() else ""
            _, carried = close_week_file(weeks_dir / f"{wid}.md", wid, issues)
            open_week_file(weeks_dir, nxt, prior_text, carried, issues)
            touched.add(f"{rel_now}/weeks/{wid}.md")
            touched.add(f"{rel_now}/weeks/{nxt}.md")
            print(f"closed {wid} → opened {nxt} (carried {len(carried)}).")
        rolled.append(nxt)
        wid = nxt

    if args.dry_run:
        print(f"[dry-run] would repoint STATE → {current}, commit + {'(no push)' if args.no_push else 'push'}.")
        return 0

    repoint_state(now_dir, current)
    touched.add(f"{rel_now}/STATE.md")
    paths = sorted(touched)
    git(now_dir, "add", "--", *paths)
    msg = f"week-roll: auto-rolled {latest} → {current} ({len(rolled)} week(s))"
    c = git(now_dir, "commit", "-m", msg, "--", *paths)
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print(f"commit failed: {c.stderr.strip()}", file=sys.stderr)
        return 1
    print(f"committed: {msg}")
    if not args.no_push:
        p = git(now_dir, "push")
        print("pushed." if p.returncode == 0 else f"push failed (record is safe locally): {p.stderr.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
