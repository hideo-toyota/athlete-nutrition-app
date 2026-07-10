#!/usr/bin/env bash
# Local-only daily build + analysis packet wrapper.
#
# Scope:
# - No network. Uses existing data/raw and data/derived only.
# - Produces investor brief, LLM handoff packet, Discord prompt, and doctor report.
# - Does not call any LLM API or place trades.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASOF="${1:-$(date +%F)}"
LOG_DIR="$ROOT/outputs/automation/$ASOF"
mkdir -p "$LOG_DIR"

cd "$ROOT" || exit 1

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

run_logged() {
  name="$1"
  shift
  log_file="$LOG_DIR/${name}.log"
  log "start: $name"
  "$@" >"$log_file" 2>&1
  status=$?
  if [ "$status" -eq 0 ]; then
    log "done: $name (log: $log_file)"
  else
    log "failed: $name status=$status (log: $log_file)"
  fi
  return "$status"
}

strict="${RADAR_STRICT_AUTOMATION:-0}"
failed=0

run_logged "daily_update" python3 -m radar daily-update --asof "$ASOF" --max-items "${RADAR_DAILY_MAX_ITEMS:-50}" || failed=1
run_logged "audit_report" python3 -m radar audit-report --asof "$ASOF" || true
run_logged "doctor" python3 -m radar doctor || failed=1

if [ "$strict" = "1" ] && [ "$failed" -ne 0 ]; then
  exit 1
fi
exit 0
