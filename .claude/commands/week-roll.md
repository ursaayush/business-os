---
description: Conclude the current ISO week and open the next — fill Shipped/Slipped, carry over open in-play issues, seed the new week, repoint STATE. Manual trigger (the Monday rollover); never invents facts.
argument-hint: [<YYYY-Www>]   (no arg = roll the week that just ended → the current week)
---

You are running `/week-roll` — the **week-rollover** for the `now/` layer. It concludes one
week and opens the next, so `weeks/*` is a true, always-current history.

**Two week-rolls exist by design:**
1. **This command — the rich, interactive roll.** Reads the real movement, writes a narrated
   Shipped/Slipped + a thoughtful Focus, flags judgment calls to the owner.
2. **`scripts/week_roll.py` — the deterministic backstop.** A no-AI program launchd runs every
   Monday (installed by `scripts/setup.sh`). If nobody opens a session for weeks, it still
   rolls every missed week (catch-up), commits, and pushes — the chain never breaks. Weeks it
   rolls are marked `(auto)`; run this command after time away to enrich them with narrative.

## Steps

1. **The week ids.** `date +%G-W%V` for the current ISO week. The week to close = the newest
   file in `now/weeks/` (or the arg); the week to open = the next ISO week + its Mon–Sun range.
   Never invent dates.
2. **Gather the real movement** (don't guess):
   - **Shipped** ← issues in `completed/` whose `closed:` falls inside the closing week, plus
     `git log --since=<weekstart> --until=<weekend>` evidence.
   - **Slipped / carried** ← issues in the closing week's `## In play` still open
     (`todo`/`doing`/`blocked`/`review`).
3. **Close the week file:** fill `## Shipped ✅` and `## Slipped / carried →` (append — never
   clobber hand-written notes), tidy `## In play`, add a log line `<date>: week rolled → <next>`.
4. **Open the next week file** from `weeks/_TEMPLATE.md`: carried issues under `## In play`;
   `**Focus:**` seeded from the active intents + the closing week's `## Next week` + top open
   priorities (1–2 lines; if unsure, write a conservative focus and ask the owner).
5. **Repoint STATE:** update `STATE.md`'s "This week →" line + "Last updated".
6. **Show, then commit.** Summarize what shipped, what carried, the new focus — flag judgment
   calls to the owner rather than guessing. Commit (and push if a remote exists).

## Guardrails
- **Never invent** shipped/slipped items — every entry traces to git, an issue's `closed:`, or
  `completed/`.
- An issue only "shipped" if it's truly `done`/in `completed/` — `review` carries, it didn't ship.
- One week closed + one opened per run; idempotent (re-running a done roll is a no-op + a note).
