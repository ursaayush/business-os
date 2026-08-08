# now/ — the operational layer (the running machine)

This folder is the **operational layer**: *what's happening right now, what we're working on
this week, the open issues, and the intents.* It is the third tier of the operating system —

```
brain/   = WHY   — the owner's thinking, decisions, insights     (durable)
studio/  = HOW   — methods, playbooks, the quality bar           (durable)
now/     = NOW   — current state, this week, issues, intents     (living)   ← you are here
```

The job of `now/` is the job of a **project manager**: make sure nothing is loose and
everything is connected. It holds the thin "what's active + the cadence" layer; deep detail
lives in `brain/` and `studio/`, and `now/` points into them.

## ⛔ THE PRIME DIRECTIVE — close what you open (read before touching ANY issue)

**An issue you start is an issue you finish.** The agent that moves an issue into `doing` owns
it to a **terminal state in the same session** — `doing` means *"being worked right now, by
me"*, never a parking spot. Non-negotiable:

1. **`doing` = active this session.** If you stop before it's truly done, set the **true**
   status before you end the turn — never leave it `doing`:
   - `review` — the work is done; the **owner** must look / approve / decide (say what you need).
   - `blocked` — name the blocker **and** who unblocks it.
   - `dropped` — say why (a reversed or abandoned call).
2. **Finish beats start.** Don't open a second issue while the first is unfinished.
3. **Don't grow the board with junk.** A new issue is created **only when it's the unit of
   active, about-to-be-worked work** — never a backlog dump or a "someday" note. If it won't be
   worked-and-closed soon, note it in STATE or the week file instead, or fold it into an
   existing issue.
4. **Keeping state true is part of "done."** Every session that touches an issue updates its
   `status` + the INDEX row + `STATE.md`; on finish, fill `Changed`, check `Done when`, move
   the file to `completed/<YYYY-MM>/`.
5. **Sweep the rot.** If you pass an issue sitting in `doing` with no recent movement, re-state
   it (`review`/`blocked`/`dropped`) — don't walk past it.

> The bar: a **small, true board** — every row is either *being worked now*, *waiting on a
> named human action*, or *gone*. If the board grows faster than `completed/`, we are failing.

## Operating principles

1. **Files are the source of truth.** Plain markdown, versioned by git. Any tool or view ever
   built on top is downstream — never the owner of the state.
2. **Agents keep it un-stale.** Every session reads [`STATE.md`](STATE.md) at the start and
   updates it (+ the week + issues) at the end. Two scheduled helpers back this up: the daily
   **now-doctor** (auto-fixes mechanical drift) and the Monday **week-roll**. See
   [`../OPERATIONS.md`](../OPERATIONS.md).
3. **Lightweight, extend as we go.** Start minimal; add structure only when the work needs it.
4. **Everything connects.** Weeks reference issues by `#id`; issues ladder to an **intent**;
   the intent frames the week.

## What's in here

| File | What it holds |
|---|---|
| [`STATE.md`](STATE.md) | **The heartbeat.** One screen: what's on the owner, what's in flight, what's next. *Read first.* Kept ≤ ~60 lines — a snapshot, not a log. |
| [`intents.md`](intents.md) | **Intents** — the outcomes we're driving toward; issues ladder to them via `intent:`. |
| [`issues/INDEX.md`](issues/INDEX.md) | **The board** — open issues grouped by area (id · status · priority · owner · due · intent) + the Completed roster. |
| `issues/<area>/<id>-<slug>.md` | One file per issue, filed by area: `personal` · `business` · `tech`. IDs are global. |
| `issues/completed/<YYYY-MM>/` | Finished issues, filed by the month they closed. Keeps the open board lean; keeps the full record. |
| `issues/dropped/` | "Won't do" issues (`status: dropped`, with a one-line why). Off the board, never deleted. |
| `weeks/<YYYY-Www>.md` | One file per ISO week — focus · in play · shipped · slipped · log · next. The weekly record. |
| `*/_TEMPLATE.md` | The capture format for issues and weeks. |

## The issue model (keep it bulletproof)

Every issue is its own file at `issues/<area>/<id>-<slug>.md` with frontmatter:

- **id** — an increasing integer, **never reused**. Next id = (max on the board) + 1.
- **status** — `todo` · `doing` · `blocked` · `review` · `done` · `dropped`.
- **priority** — `P0` (now/critical) · `P1` (this cycle) · `P2` (soon) · `P3` (someday).
- **owner** — the next actor: `me` (the owner — a decision, or something only they can do)
  or `agent` (the AI can progress it). This is the delegation split.
- **due** — target date (`YYYY-MM-DD`) when slated; blank = unscheduled.
- **area** — `personal` · `business` · `tech`.
- **intent** — the outcome it serves (a slug from [`intents.md`](intents.md)). Optional.
- **slated** — an ISO week (`2026-W32`) or `backlog`. **closed** — the done date.
- **links** — the deepest home (a `brain/` capture, a `studio/` playbook, a repo, a URL).

**Lifecycle:** `todo`/`doing` → on finish: fill the `Changed` section (what changed, where),
set `status: done` + `closed:`, move the file to `completed/<YYYY-MM>/` (bump internal links
one `../` deeper), and move its board row to the Completed roster. Never delete.

## How to use it (for agents)

- **Start of a session:** read `STATE.md` + the current `weeks/` file. That's the running context.
- **During:** take on / finish / block something → update its issue + `STATE.md`.
- **End of a session:** reconcile — STATE, the week file, issue statuses. Then commit.
- **Decision made along the way?** → log it in [`../brain/decisions.md`](../brain/decisions.md);
  `now/` only tracks the *doing* of it.
