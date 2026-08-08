#!/bin/bash
# Wrapper for the deterministic now/ doctor (run by launchd, com.businessos.now-doctor).
# launchd starts bare — set a sane PATH so python3 + git resolve. Default mode auto-fixes the
# mechanical drift (done→completed/<month>/, INDEX↔frontmatter, the completed roster) and
# commits + pushes; idempotent (a clean tree ⇒ no commit). Logs every run; never fails loudly.
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
{
  echo "=== now_doctor $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  python3 scripts/now_doctor.py "$@"
  # Verify: after the doctor fixes the mechanical drift, assert the now/ folder is healthy.
  # A FAILED here = something the doctor can't auto-fix — surfaced in this log + now/HEALTH.md.
  echo "--- now/ health suite (verify) ---"
  python3 -m unittest scripts.test_now_health 2>&1 | tail -4
  echo ""
} >> scripts/now_doctor.log 2>&1
