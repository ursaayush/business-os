#!/usr/bin/env bash
# Business OS bootstrap — turn on the automation on THIS Mac.
#
# Idempotent + path-portable: it derives every path from where this folder actually sits, so
# it works on any Mac, any user, wherever the folder lives. Safe to re-run anytime.
# What it installs (full inventory: OPERATIONS.md):
#   • com.businessos.week-roll  — every Monday 09:05 (+ on boot): rolls the week forward.
#   • com.businessos.now-doctor — every morning 08:30 (+ on boot): tidies the issue board.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LA_DIR="$HOME/Library/LaunchAgents"
PY="$(command -v python3 || true)"
mkdir -p "$LA_DIR"

say()  { printf "\033[1m• %s\033[0m\n" "$*"; }
warn() { printf "\033[33m⚠ %s\033[0m\n" "$*"; }

say "Business OS root: $ROOT"
[ -n "$PY" ] || warn "python3 not found — the helpers need it (it ships with macOS dev tools: xcode-select --install)."
command -v git >/dev/null || warn "git not found — the helpers can't save their work without it."

install_agent() {  # label, program, calendar-xml
  local LABEL="$1" PROG="$2" CAL="$3" PLIST="$LA_DIR/$1.plist"
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PROG</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key><dict>$CAL</dict>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$ROOT/scripts/$LABEL.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/scripts/$LABEL.err.log</string>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLIST
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load -w "$PLIST" && say "  loaded $LABEL"
}

say "Installing com.businessos.week-roll (Mondays 09:05 + boot)…"
chmod +x "$ROOT/scripts/week_roll.sh" "$ROOT/scripts/week_roll.py" 2>/dev/null || true
install_agent com.businessos.week-roll "$ROOT/scripts/week_roll.sh" \
  "<key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>5</integer>"

say "Installing com.businessos.now-doctor (daily 08:30 + boot)…"
chmod +x "$ROOT/scripts/now_doctor.sh" "$ROOT/scripts/now_doctor.py" 2>/dev/null || true
install_agent com.businessos.now-doctor "$ROOT/scripts/now_doctor.sh" \
  "<key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer>"

say "Bootstrap done. To check things ran:"
cat <<STEPS
  • launchctl list | grep businessos
  • python3 scripts/week_roll.py --dry-run
  • python3 scripts/now_doctor.py --check
Note: the helpers 'git push' when a GitHub remote is set up — run one push by hand first so
the Mac remembers the credentials (the onboarding covers this).
STEPS
