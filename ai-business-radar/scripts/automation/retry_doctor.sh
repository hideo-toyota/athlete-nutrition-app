#!/usr/bin/env bash
# Morning retry/diagnostic wrapper.
#
# Default is local-only. Set RADAR_RETRY_FETCH=1 explicitly to re-run network
# fetch in the morning.
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

if [ "${RADAR_RETRY_FETCH:-0}" = "1" ]; then
  log "RADAR_RETRY_FETCH=1; running daily_fetch"
  "$ROOT/scripts/automation/daily_fetch.sh" "$ASOF" >"$LOG_DIR/retry_fetch.log" 2>&1 || true
fi

if [ ! -f "$ROOT/outputs/investor_brief/$ASOF.md" ]; then
  log "investor brief missing; running build_and_brief"
  "$ROOT/scripts/automation/build_and_brief.sh" "$ASOF" >"$LOG_DIR/retry_build_and_brief.log" 2>&1 || true
else
  log "investor brief exists; skip rebuild"
fi

python3 -m radar doctor >"$LOG_DIR/retry_doctor.log" 2>&1 || true
log "retry_doctor finished (log: $LOG_DIR/retry_doctor.log)"
