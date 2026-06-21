#!/usr/bin/env bash
# Safe periodic pull of the dev branch on the Mac.
#
# Design (discipline):
# - Fast-forward ONLY. If local work diverged (e.g. Codex committed locally) or
#   the tree is dirty, it SKIPS — it never clobbers, resets, or force-pulls.
# - Only updates files. It does NOT run fetch-jquants / build / analysis. Code
#   delivery is automatic; execution stays manual and permission-gated.
# - No secrets are read or printed. Logs go to a temp file outside the repo so
#   the working tree never becomes dirty from logging.
set -uo pipefail

BRANCH="${RADAR_BRANCH:-claude/discord-ai-agent-setup-NCvKl}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="${TMPDIR:-/tmp}/radar_auto_pull.log"

cd "$REPO_ROOT" || exit 0
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') auto-pull ($BRANCH) @ $REPO_ROOT ==="
  if [ -n "$(git status --porcelain)" ]; then
    echo "skip: working tree has local changes (leaving untouched)"
    exit 0
  fi
  current="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$current" != "$BRANCH" ]; then
    echo "skip: current branch is '$current', not '$BRANCH'"
    exit 0
  fi
  git fetch origin "$BRANCH" || { echo "fetch failed (offline?) — will retry next run"; exit 0; }
  if git merge-base --is-ancestor HEAD "origin/$BRANCH"; then
    git merge --ff-only "origin/$BRANCH" && echo "updated to $(git rev-parse --short HEAD)"
  else
    echo "skip: local commits not on remote (diverged) — not fast-forwardable, untouched"
  fi
} >> "$LOG" 2>&1
