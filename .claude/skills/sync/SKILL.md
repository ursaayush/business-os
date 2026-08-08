---
name: sync
description: Keep the operational layer (now/) current, never stale. Use when the owner says "/sync", "what's the plan", "where are we", "standup", at the start of a session after time away, or whenever the board looks out of date. Reconciles now/ against what actually happened, gives the owner a plain-words standup, and writes the truth back.
---

# Sync — keep `now/` true

The operational layer (`now/`) is only useful if it's **true right now**. This skill is the
anti-staleness engine: it reconciles `now/` against what *actually* happened (git history +
the real files), gives the owner a plain-words standup, captures what changed, and writes it
back. It is the operational twin of `grill-me` (which keeps `brain/` current). The daily
`now_doctor` script fixes *mechanical* drift automatically; this is the *thinking* layer.

## What it does (the loop)

### 1. Read the current state
`now/STATE.md` · `now/issues/INDEX.md` · the current `now/weeks/<ISO-week>.md` · `now/intents.md`
· [`brain/grill-plan.md`](../../../brain/grill-plan.md) (what's still uncaptured).

### 2. Detect what actually moved (evidence, not memory)
- `git log --since="<last STATE update>" --oneline` — what really happened.
- Any issue whose linked work is clearly done or blocked?
- Compute the ISO week (`date +%G-W%V`). New week since the latest `weeks/` file? A roll-over
  is due → [`week-roll`](../../commands/week-roll.md).

### 3. Standup — show the owner the picture, plain
- **Done since last time** (from git + issues).
- **On you** vs **on me** — split open issues by `owner`, so it's clear what needs the owner
  (a decision, a recording, a yes) vs what the AI is progressing.
- **Overdue / stuck** — anything past its `due` or with no movement → offer to reschedule or
  drop it (dropped, with a one-line why — a shorter honest board beats a long stale one).
- **Up next** — the recommended focus, one line.
- **Still uncaptured** — if the grill plan has open rows, offer the next one (once, gently).

### 4. Capture what changed — ask, don't assume
Where evidence is ambiguous, ask one question at a time with a recommended answer (grill-me
style): did X actually get finished? Is this still the focus? Anything unambiguous, just
propose the update.

### 5. Write it back (the durable part)
- Update `now/STATE.md` (refresh + the date; keep it a small snapshot — history goes to the
  week file).
- Update issue files + `INDEX.md`. New issues get the next id (never reuse). **On done:** fill
  `Changed`, set `status: done` + `closed:`, move the file to `completed/<YYYY-MM>/`, update
  the roster.
- Update the current `weeks/` file (Shipped / Slipped / Notes / Next).
- A decision surfaced? → one line in `brain/decisions.md`.
- **Commit** (and push if a remote is set up).

## Rules
- **Evidence first.** Don't mark something done unless the files/git say so or the owner
  confirms it.
- **Never reuse an issue id.**
- **Stay lightweight.** A row is enough for most issues.
- **Unattended-safe.** If run with no human present, do the unambiguous writes only and leave
  a "needs the owner" note in `STATE.md` for the rest — never guess.

## Voice
A sharp, friendly chief-of-staff doing a 60-second standup. Plain and concrete. The point is
the owner feels the machine is **running and nothing is loose.**
