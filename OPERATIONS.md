# OPERATIONS — what runs automatically, and how to set up a new machine

> **This folder is the truth.** Copy it to any Mac, run one bootstrap, and the operating
> system comes back to life. This doc is the inventory of everything that runs + the runbook
> to make it run anywhere. If you add a job, add it here and to
> [`scripts/setup.sh`](scripts/setup.sh).

## New machine — TL;DR

```bash
cd <wherever-this-folder-lives>
bash scripts/setup.sh
```

`setup.sh` is **idempotent** (safe to re-run) and **path-portable** (it derives every path
from where the folder actually sits). If the folder came fresh from GitHub
(`git clone <the-owner's-repo-url>`), run one `git push` by hand afterwards so the Mac caches
the credentials — the helpers push their own commits.

## The inventory (what runs)

| Job | What it does | Trigger |
|---|---|---|
| **`com.businessos.week-roll`** | Runs [`scripts/week_roll.py`](scripts/week_roll.py): closes the ended week, opens the next, carries open work, commits + pushes. No AI involved — pure, deterministic, idempotent. Catch-up built in: away N weeks → one run rolls all N. | launchd: Mondays 09:05 + on boot |
| **`com.businessos.now-doctor`** | Runs [`scripts/now_doctor.py`](scripts/now_doctor.py): auto-fixes mechanical board drift (done issues filed into `completed/<month>/`, INDEX rows matching issue files, the roster), writes [`now/HEALTH.md`](now/HEALTH.md), commits + pushes. Flags judgment calls instead of guessing. Then runs the health test suite. | launchd: daily 08:30 + on boot |

Both log to `scripts/*.log` (gitignored). Neither needs the internet except for the push, and
a failed push is safe — the record stays local until the next one succeeds.

## Manual checks (anytime)

```bash
launchctl list | grep businessos          # are both helpers installed?
python3 scripts/week_roll.py --dry-run    # what would the next roll do?
python3 scripts/now_doctor.py --check     # board health report (also written to now/HEALTH.md)
python3 scripts/test_now_health.py        # the full test suite
```

## What still needs a human

- **GitHub credentials** — one manual `git push` after cloning (macOS remembers after that).
- **Claude Code sign-in** — the AI assistant signs in per machine.
- That's the whole list, by design.
