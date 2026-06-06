#!/usr/bin/env bash
# launchd から呼ばれる日次バッチ。Claude Code をヘッドレスで起動し /daily-report を実行する。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 仮想環境があれば有効化
if [[ -f "${ROOT_DIR}/.venv/bin/activate" ]]; then
  source "${ROOT_DIR}/.venv/bin/activate"
fi

# サブスク利用時は従量課金APIキーを無効化(意図しない課金防止)
unset ANTHROPIC_API_KEY || true

LOG_DIR="${ROOT_DIR}/reports/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"

echo "[$(date)] daily run start" >> "${LOG_DIR}/run.log"

# caffeinate で実行中のスリープを防止しつつ、Claude Code をヘッドレス実行。
# 非対話なので権限は .claude/settings.json の allow リストに従う。
caffeinate -i claude -p "/daily-report" \
  --permission-mode acceptEdits \
  > "${LOG_DIR}/report_${STAMP}.log" 2>&1 || {
    echo "[$(date)] daily run FAILED (see report_${STAMP}.log)" >> "${LOG_DIR}/run.log"
    "${ROOT_DIR}/scripts/notify.sh" --alert "⚠️ ai-analyst の日次バッチが失敗しました(${STAMP})" || true
    exit 1
  }

echo "[$(date)] daily run done" >> "${LOG_DIR}/run.log"
