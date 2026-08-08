#!/bin/bash
# Wrapper for the deterministic week-roll (run by launchd, com.businessos.week-roll).
# Sets a sane PATH (launchd starts bare) so python3 + git resolve, logs every run,
# and never fails loudly — the roll is idempotent + safe to retry.
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
{
  echo "=== week_roll $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  python3 scripts/week_roll.py "$@"
  echo ""
} >> scripts/week_roll.log 2>&1
