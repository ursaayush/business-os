#!/usr/bin/env python3
"""test_now_health — asserts the REAL now/ folder is healthy. The always-on guarantee.

now_doctor.py *fixes* the mechanical drift; THIS suite *asserts the result is clean* — so the
board stays true and nothing is silently drifting. Every failure names the exact issue(s) at
fault.

Run it: `python3 scripts/test_now_health.py` (or `python3 -m unittest scripts.test_now_health`).
Run it before a push, on demand, or on the schedule (the daily now_doctor verifies the same checks).
Override the target with NOW_DIR=/path/to/now.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import now_doctor as nd  # noqa: E402

NOW = Path(os.environ.get("NOW_DIR", Path(__file__).resolve().parent.parent / "now")).resolve()

VALID_STATUS = {"todo", "doing", "blocked", "review", "done", "dropped"}
VALID_PRIORITY = {"", "p0", "p1", "p2", "p3"}
VALID_OWNER_NONEMPTY = True


def numbered_issue_files(now: Path):
    """Every issue-shaped file: issues/**/<digits>-*.md, excluding templates/INDEX/README/CONTRACT."""
    for p in sorted((now / "issues").rglob("*.md")):
        if p.name.startswith("_") or p.name in nd.SKIP_NAMES:
            continue
        if re.match(r"^\d+-", p.name):
            yield p


class BoardContract(unittest.TestCase):
    """The invariants every issue file must hold — the frontmatter schema everything (agents,
    scripts, any future view) keys on. Break these and files silently fall off the board."""

    @classmethod
    def setUpClass(cls):
        cls.files = list(numbered_issue_files(NOW))
        cls.issues = nd.load_issues(NOW)

    def test_every_issue_file_has_valid_frontmatter_and_id(self):
        bad = []
        for p in self.files:
            text = p.read_text(encoding="utf-8", errors="replace")
            if not text.startswith("---") or text.find("\n---", 3) == -1:
                bad.append(f"{p.name}: no/!terminated YAML frontmatter — the parser would drop it")
                continue
            fm, _ = nd.parse_frontmatter(text)
            if "id" not in fm or not re.fullmatch(r"\d+", (fm.get("id") or "").strip()):
                bad.append(f"{p.name}: missing/!integer `id` — the join key everything keys on")
        self.assertEqual([], bad, "\n" + "\n".join(bad))

    def test_ids_unique(self):
        seen, dups = {}, []
        for iss in self.issues:
            if iss.id is None:
                continue
            if iss.id in seen:
                dups.append(f"#{iss.id}: {seen[iss.id]} and {iss.path.name}")
            seen[iss.id] = iss.path.name
        self.assertEqual([], dups, "duplicate ids (ids must be global + never reused):\n" + "\n".join(dups))

    def test_required_fields_present(self):
        bad = []
        for iss in self.issues:
            for f in nd.REQUIRED_FIELDS:
                if not (iss.fm.get(f) or "").strip():
                    bad.append(f"#{iss.id} {iss.path.name}: missing `{f}`")
        self.assertEqual([], bad, "\n" + "\n".join(bad))

    def test_status_and_priority_enums(self):
        bad = []
        for iss in self.issues:
            if iss.status and iss.status not in VALID_STATUS:
                bad.append(f"#{iss.id}: status `{iss.status}` not in {sorted(VALID_STATUS)}")
            if (iss.priority or "").lower() not in VALID_PRIORITY:
                bad.append(f"#{iss.id}: priority `{iss.priority}` not in P0–P3")
        self.assertEqual([], bad, "\n" + "\n".join(bad))

    def test_state_hero_id_resolves(self):
        """STATE.md `## Right now`'s first #id must resolve to a real issue — the current focus."""
        state = (NOW / "STATE.md").read_text(encoding="utf-8")
        m = re.search(r"##\s*Right now.*?(?=\n##\s|\Z)", state, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(m, "STATE.md has no `## Right now` section")
        ids = re.findall(r"#(\d+)", m.group(0))
        self.assertTrue(ids, "STATE.md `## Right now` has no #id for the hero card")
        known = {iss.id for iss in self.issues}
        self.assertIn(int(ids[0]), known, f"STATE hero #{ids[0]} resolves to no issue")


class NoDrift(unittest.TestCase):
    """The mechanical layer now_doctor keeps fixed — after it runs, the board must be clean. We run
    the doctor in check mode (no writes) and assert zero flags of each drift class; the message lists
    every offending item so you know exactly what's wrong."""

    @classmethod
    def setUpClass(cls):
        cls.findings, _ = nd.run(NOW, apply=False)

    def _flags(self, *checks):
        return [f.msg for f in self.findings if f.level == "flag" and f.check in checks]

    def test_no_integrity_problems(self):
        f = self._flags("A")
        self.assertEqual([], f, "duplicate/missing ids or fields:\n" + "\n".join(f))

    def test_done_and_dropped_are_filed_off_the_board(self):
        f = self._flags("B", "B2")
        self.assertEqual([], f, "done/dropped issues not in completed/<month>/ or dropped/:\n" + "\n".join(f))

    def test_index_matches_frontmatter(self):
        f = self._flags("C", "C2")
        self.assertEqual([], f, "INDEX board ≠ issue frontmatter (frontmatter wins):\n" + "\n".join(f))

    def test_completed_roster_current(self):
        f = self._flags("D")
        self.assertEqual([], f, "INDEX completed roster ≠ the completed/ folders:\n" + "\n".join(f))

    def test_state_within_budget(self):
        f = self._flags("E")
        self.assertEqual([], f, "STATE.md drifted (over budget / no hero):\n" + "\n".join(f))

    def test_no_broken_links(self):
        f = self._flags("F")
        self.assertEqual([], f, "broken relative links (a moved/renamed target):\n" + "\n".join(f))


if __name__ == "__main__":
    unittest.main(verbosity=2)
