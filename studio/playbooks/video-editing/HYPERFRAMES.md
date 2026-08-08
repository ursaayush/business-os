# HyperFrames — videos the AI builds for you

> The third way to make videos, and the one this system leans on most: instead of you dragging
> clips around in an editor, **you describe the video and the AI builds it** — animated text,
> captions, voiceover, music, your footage, all combined by code and rendered to a finished
> file. It's called **HyperFrames**: videos built like web pages, which is exactly what an AI
> is great at writing.

## When to use what (the full picture)

| The video is… | Use |
|---|---|
| Raw footage you want to trim and arrange by hand | iMovie / CapCut ([`README.md`](README.md)) |
| Talking-head with a swapped background | [`GREEN-SCREEN.md`](GREEN-SCREEN.md) |
| Anything with **animated text, captions, voiceover, titles, social-style motion** — explainers, promos, quote cards, reels with word-by-word captions | **HyperFrames — ask the AI** |

In practice most business videos are a mix: you film yourself once, then the AI wraps it in
hooks, captions, and titles with HyperFrames. You never touch the code.

## What to say (that's your whole job)

Talk to the AI in plain words, like briefing an editor:

- *"Make a 30-second promo from this clip — big captions, my logo at the end."*
- *"Turn this voice memo into a video: my voice, animated text over a calm background."*
- *"Add word-by-word captions to this video, they should pop as I speak."*
- *"Cut my background out of this clip and put me over the office image."*

The AI will show you a **preview** in the browser. You react in normal words — "captions
bigger", "slower", "less bouncy", "that yellow is ugly" — until it feels right. Then it
renders the final file into your video folder's `exports/`. That loop — describe → preview →
react → render — is the whole workflow.

## What it can do (so you know what to ask for)

- **Word-synced captions** — it *listens* to your audio (transcription) and times every word.
- **Voiceover from text** — write (or dictate) a script; it generates a natural voice. Great
  for videos where you don't want to be on camera.
- **Background removal** — software green screen, built in (see GREEN-SCREEN.md Option A).
- **Animated text & titles** — kinetic typography, highlights, hand-drawn circles, transitions.
- **Audio-reactive visuals** — graphics that pulse with the music.
- **Ready-made styles** — a public registry of caption styles, transitions, and lower-thirds
  the AI can pull in, so videos look designed from day one.

---

## For the agent (the technical corner — the owner never reads this)

HyperFrames is an open toolchain driven by the `npx hyperframes` CLI (needs Node.js — install
it for the owner if missing, explaining in one plain line). Compositions are deterministic,
seek-driven HTML; you author them, the owner only ever sees previews and finished files.

- **Environment:** `npx hyperframes doctor` first (checks browser + render env). Scaffold with
  `npx hyperframes init` (per-video project, keep it inside the video's folder next to
  `footage/`).
- **Dev loop:** `lint` → `preview` (show the owner, iterate) → `render` (final file →
  `exports/`).
- **Media preprocessing:** `npx hyperframes tts` (voiceover from script), `transcribe`
  (Whisper — feeds word-synced captions), `remove-background` (u2net — the software green
  screen). Each downloads its model on first run — warn the owner the first one takes a few
  minutes.
- **Registry:** `npx hyperframes add <item>` installs caption styles / transitions /
  lower-thirds; prefer registry blocks over hand-rolling.
- **Skills:** if HyperFrames agent skills are installable in this environment (check the
  skills marketplace / `find-skills`), install them — they carry the full authoring patterns
  (composition timing, adapters for GSAP/CSS/Lottie, caption pipelines). Otherwise the CLI's
  scaffold + docs are self-describing.
- **Quality bar as always:** watch the rendered file start to finish before showing it as
  done ([`../../production/QUALITY-GATE.md`](../../production/QUALITY-GATE.md) — checks 6–9
  apply in full).
