---
name: onboard
description: The fully guided first-run setup for a brand-new owner of this Business OS. Use when the owner says "set me up", "get me started", "onboard me", when the "Getting set up" checklist in START-HERE.md has unchecked boxes, or whenever a fresh session lands in this folder and setup looks incomplete. Resumable — it picks up at the first unchecked step.
---

# Onboard — set a new owner up, gently, one step at a time

The owner of this folder is **not technical**. They may never have used a terminal, git, or
GitHub. Your job is to get them fully set up without them ever feeling lost or stupid.

## The ground rules (these override everything)

1. **One step per turn.** Do a step, show the result in one plain sentence, say what's next,
   wait. Never dump the whole plan or a wall of instructions.
2. **You do the technical work.** Run the commands yourself. The owner only does what genuinely
   requires a human: typing their own passwords, clicking buttons in their own browser.
3. **Never touch their credentials.** You must not create accounts for them or enter passwords
   for them — when a step needs that (GitHub sign-up, sign-in), explain exactly what to click
   in their browser, in numbered baby steps, and wait until they say it's done.
4. **Explain the why in one line, always.** "We're doing this so your work is backed up" beats
   any technical explanation. No jargon — if a technical word must appear, define it in the
   same breath ("GitHub — a free website that keeps a safe copy of this folder").
5. **Resumable.** The checklist in [`START-HERE.md`](../../../START-HERE.md) is the state.
   Start at the first unchecked box. Tick each box (change `[ ]` to `[x]`) the moment its step
   truly completes, and commit.
6. **Patient and warm, never patronizing.** They're smart — just new to this.

## The steps

### Step 1 — Meet & tour

Introduce yourself as their business assistant. Ask what they'd like to be called. Then the
2-minute tour, in plain words:

> This folder is your business's home base. Three rooms: **brain/** is your thinking — I only
> write there what you actually tell me. **studio/** is your methods — there's already a guide
> for video editing waiting for you. **now/** is what's happening — your week, your to-do
> board. You talk to me; I keep all of it organized, current, and backed up.

Ask if they want more detail or are happy to move on. Tick box 1.

### Step 2 — Personalize

Ask (one at a time, suggest an answer where you can):
- Their name.
- The business's name (or working name — "we can change it anytime").
- One sentence on what the business does or will do (don't push — the deep capture is Step 5).

Write [`OWNER.md`](../../../OWNER.md) at the folder root:

```markdown
# Owner
- **Name:** <name>
- **Business:** <business name>
- **In one line:** <their sentence>
- **Set up on:** <YYYY-MM-DD>
```

Set their name in git so their saves are signed correctly (run it for them):
`git config user.name "<name>"` and `git config user.email "<their email>"` (ask for the email
they'll use for GitHub in Step 3 — kill two birds). Make the first commit. Tick box 2.

### Step 3 — Back up on GitHub

Explain the why first: *"Right now this folder lives only on this laptop. GitHub is a free
website that keeps a private, safe copy — if the laptop breaks, nothing is lost. Setting it up
takes about five minutes and you only do it once."*

Then, adapt to what's on the machine (check quietly with `git --version`, `command -v gh`):

1. **Git missing?** Run `xcode-select --install` for them and explain the popup they'll see
   ("your Mac is installing its standard developer kit — takes a few minutes").
2. **GitHub account.** If they don't have one: walk them through https://github.com/signup in
   their own browser, numbered baby steps (email → password → username). They type everything;
   you wait. Suggest a sensible username. Remind them to save the password in their password
   manager or keychain.
3. **Connect this folder.** Prefer the GitHub CLI if present (`gh auth login` — tell them a
   browser window will open and they just click "Authorize"; the one-time code flow is
   newbie-friendly). If `gh` is missing, either install it (ask first) or fall back to
   creating the repository on github.com by hand — guide the clicks: New repository → name it
   (suggest the business name, lowercased) → **Private** → Create.
4. **⚠️ Their own private repo, always.** This folder usually arrives as a clone of the
   **public starter kit** (`github.com/ursaayush/business-os`) — check with
   `git remote get-url origin`. If origin points there (or anywhere that isn't the owner's own
   account), you MUST re-point it before the first push: create the owner's own **private**
   repo and `git remote set-url origin <their-repo-url>`. **The owner's business data must
   never be pushed to the public starter repo** — it's public, and it isn't theirs.
5. **First push.** Push, then show them the proof: tell them to refresh their GitHub page and
   see their folder online. That moment matters — let them enjoy it.

Tick box 3.

### Step 4 — Turn on the automation

Explain in one line each:
- *"A little helper runs every Monday morning and rolls your week forward — closes last week's
  page, opens a fresh one, carries over unfinished work."*
- *"Another runs every morning and tidies the board — files finished tasks away, fixes small
  inconsistencies."*

Ask for a yes, then run `bash scripts/setup.sh` and confirm both helpers installed
(`launchctl list | grep businessos`). If anything fails, fix it yourself; only involve the
owner if their password is genuinely required (say exactly why). Tick box 4.

### Step 5 — Capture the business (the first grill)

Explain: *"Now the fun part. I'll interview you about your business — one question at a time,
and I'll suggest an answer to each so you can just say 'yes' or correct me. Everything you say
gets saved in your own words. Twenty minutes, and afterwards I genuinely know your business."*

Run the [`grill-me`](../grill-me/SKILL.md) skill, scoped for a first session (~8–12 questions):
what the business is · who it's for · what they sell (or will sell) · what "going well" looks
like in 6 months · what they're best at · what scares them about it · what the first concrete
goal is. Capture to `brain/sessions/`, then synthesize into `brain/operating-system.md` and
seed a first draft of `studio/POSITIONING.md` (clearly marked as a draft to refine).

That first session ticks row 1 of [`brain/grill-plan.md`](../../../brain/grill-plan.md) — the
fill-up tracker. Show it to the owner: *"these seven short interviews, over the next days or
weeks, teach me your whole business — we just did the first."* From now on every session
gently offers the next one until all are ✅.

Since their first real work is **video editing**, end by pointing at
[`studio/playbooks/video-editing/README.md`](../../../studio/playbooks/video-editing/README.md):
*"whenever you're ready to edit your first video, just say so — there's a guide waiting and
I'll walk you through it."* Tick box 5.

### Step 6 — Plan the first week

From the grill, propose 2–4 first issues (concrete, finishable — e.g. "edit my first video",
"pick the business name", "set up the green screen"). Get a yes on each, open them on the board
(`now/issues/`), set the week file's focus, update `now/STATE.md`, and tick box 6.

Close warmly: *"You're all set. From now on, just open this folder and talk to me — 'what's
the plan today?' is always a good start."* Commit and push everything.

## If setup was interrupted

Someone may say "set me up" when half the boxes are ticked. Never redo a ticked step — glance
at the checklist, confirm the ticked ones still hold (OWNER.md exists, remote configured), and
continue from the first unchecked box with a one-line recap: *"Welcome back — you're set up
through GitHub; next is turning on the automation."*
