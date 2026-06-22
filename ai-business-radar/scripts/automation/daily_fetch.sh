#!/usr/bin/env bash
# Nightly network data fetch wrapper.
#
# Scope:
# - Network data refresh only. No research queue, evidence, LLM API, or trading.
# - EDINET writes raw. Optional J-Quants watchlist REST writes derived because
#   the current formal CLI is on-demand fetch+derived, not broad raw sync.
# - Continue across failures and write logs under outputs/automation/<asof>/.
# - Never print .env contents or API key values.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ASOF="${1:-$(date +%F)}"
LOG_DIR="$ROOT/outputs/automation/$ASOF"
STATE_DIR="$ROOT/data/metadata/automation"
mkdir -p "$LOG_DIR" "$STATE_DIR"

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

latest_file() {
  pattern="$1"
  # shellcheck disable=SC2086
  ls $pattern 2>/dev/null | sort | tail -n 1
}

codes_csv_from_file() {
  file="$1"
  python3 - "$file" <<'PY'
import sys
from pathlib import Path
codes = []
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    text = line.strip()
    if not text or text.startswith("#"):
        continue
    codes.append(text.split()[0])
print(",".join(codes))
PY
}

update_edinet_offset() {
  log_file="$1"
  state_file="$2"
  next_offset="$(sed -n 's/.*next_offset: \([0-9][0-9]*\).*/\1/p' "$log_file" | tail -n 1)"
  end_offset="$(sed -n 's/.*end_offset: \([0-9][0-9]*\).*/\1/p' "$log_file" | tail -n 1)"
  if [ -z "$next_offset" ]; then
    return 0
  fi
  if [ -n "$end_offset" ] && [ "$next_offset" -ge "$end_offset" ]; then
    printf '0\n' >"$state_file"
  else
    printf '%s\n' "$next_offset" >"$state_file"
  fi
}

run_logged "data_check_offline" python3 -m radar data-check --offline

if [ "${RADAR_FETCH_COMPANIES:-1}" != "0" ]; then
  run_logged "edinet_companies" \
    python3 -m radar sync --provider edinet-db --dataset companies \
    --asof "$ASOF" --page "${RADAR_EDINET_COMPANIES_PAGE:-1}" \
    --per-page "${RADAR_EDINET_COMPANIES_PER_PAGE:-100}"
fi

codes_file="${RADAR_EDINET_CODES_FILE:-}"
if [ -z "$codes_file" ]; then
  codes_file="$(latest_file "$ROOT/data/metadata/edinetdb_company_codes_*.txt")"
fi

if [ -n "$codes_file" ] && [ -f "$codes_file" ]; then
  state_file="$STATE_DIR/edinet_financials_offset.txt"
  offset="$(cat "$state_file" 2>/dev/null || printf '0')"
  case "$offset" in
    ''|*[!0-9]*) offset=0 ;;
  esac
  limit="${RADAR_EDINET_LIMIT:-400}"
  fin_log="$LOG_DIR/edinet_financials.log"
  log "start: edinet_financials offset=$offset limit=$limit codes_file=$codes_file"
  python3 -m radar sync --provider edinet-db --dataset financials \
    --codes-file "$codes_file" --offset "$offset" --limit "$limit" \
    --years "${RADAR_EDINET_YEARS:-1}" --period "${RADAR_EDINET_PERIOD:-annual}" \
    --asof "$ASOF" >"$fin_log" 2>&1
  status=$?
  if [ "$status" -eq 0 ]; then
    update_edinet_offset "$fin_log" "$state_file"
    log "done: edinet_financials (log: $fin_log)"
  else
    log "failed: edinet_financials status=$status; offset not advanced (log: $fin_log)"
  fi
else
  log "skip: edinet_financials codes file not found"
fi

watchlist="${RADAR_JQUANTS_WATCHLIST:-$ROOT/data/metadata/jquants_watchlist.txt}"
if [ -f "$watchlist" ]; then
  codes="$(codes_csv_from_file "$watchlist")"
  if [ -n "$codes" ]; then
    run_logged "jquants_watchlist_rest" \
      python3 -m radar fetch-jquants --codes "$codes" --asof "$ASOF"
  else
    log "skip: jquants_watchlist_rest watchlist empty"
  fi
else
  log "skip: jquants_watchlist_rest watchlist not found"
fi

log "daily_fetch finished. This job does not build features or LLM packets."
