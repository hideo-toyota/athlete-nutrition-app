#!/usr/bin/env bash
# Discord Webhook へメッセージを投稿するヘルパー。
# 使い方:
#   ./scripts/notify.sh "本文"
#   ./scripts/notify.sh --alert "アラート本文"        # アラート用Webhookへ
#   ./scripts/notify.sh --file reports/report.md      # ファイル内容を投稿
set -euo pipefail

# .env 読み込み(スクリプトの1つ上の階層を基準)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a; source "${ROOT_DIR}/.env"; set +a
fi

WEBHOOK="${DISCORD_WEBHOOK_URL:-}"
CONTENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --alert) WEBHOOK="${DISCORD_ALERT_WEBHOOK_URL:-$WEBHOOK}"; shift ;;
    --file)  CONTENT="$(cat "$2")"; shift 2 ;;
    *)       CONTENT="$1"; shift ;;
  esac
done

if [[ -z "$WEBHOOK" ]]; then
  echo "ERROR: DISCORD_WEBHOOK_URL が未設定です(.env を確認)" >&2
  exit 1
fi
if [[ -z "$CONTENT" ]]; then
  echo "ERROR: 投稿する本文がありません" >&2
  exit 1
fi

# Discord の content は2000字上限。超過分は切り詰める。
CONTENT="${CONTENT:0:1900}"

# jq があれば安全にJSON化、無ければ python3 でエスケープ
if command -v jq >/dev/null 2>&1; then
  PAYLOAD="$(jq -nc --arg c "$CONTENT" '{content: $c}')"
else
  PAYLOAD="$(python3 -c 'import json,sys; print(json.dumps({"content": sys.argv[1]}))' "$CONTENT")"
fi

curl -sS -H "Content-Type: application/json" -X POST -d "$PAYLOAD" "$WEBHOOK" >/dev/null
echo "Discord へ投稿しました(${#CONTENT}字)"
