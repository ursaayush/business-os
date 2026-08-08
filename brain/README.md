# brain/ — the owner's thinking (the WHY)

This folder holds what's in the owner's head: what the business is, why it exists, the
decisions made, the ideas caught in passing. It is the most valuable folder in the system —
and the one with the strictest rule:

> **⛔ Nothing in `brain/` is ever invented or inferred.** Every fact here came out of the
> owner's mouth, captured in their words. Agents may *organize* it, never *author* it. If it's
> not here and the owner didn't say it, it isn't true yet — ask.

## How it fills up

The [`grill-me`](../.claude/skills/grill-me/SKILL.md) skill is the front door: a focused
interview, one question at a time, checkpointed to disk after every answer. Run it on the whole
business first, then on any topic that deserves depth ("grill me about pricing").

[`grill-plan.md`](grill-plan.md) is the **fill-up tracker** — every starter document and the
interview that fills it. Agents keep offering the next session until every row is ✅.

## What's in here

| File / folder | What it holds |
|---|---|
| [`operating-system.md`](operating-system.md) | **The living synthesis** — what the business is, who it's for, what it sells, the targets. Updated after each grill; the single best "understand this business" read. |
| [`decisions.md`](decisions.md) | **The decision log** — every meaningful call, one dated line + the why. Cheap to write, priceless a year later. |
| `sessions/` | The raw grill captures, one file per session (`YYYY-MM-DD-topic.md`, from [`_TEMPLATE.md`](_TEMPLATE.md)). Never overwritten — re-grills append. |
| `insights/` | Passing ideas, saved the moment they happen ("save this insight"). See [`insights/README.md`](insights/README.md). |
