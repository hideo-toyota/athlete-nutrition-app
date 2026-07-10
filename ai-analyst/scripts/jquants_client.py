#!/usr/bin/env python3
"""J-Quants API クライアント雛形。

J-Quants (日本取引所グループ公式の個人向け株式データAPI) からデータを取得します。
認証は .env の以下のいずれかを使用:
  - JQUANTS_REFRESH_TOKEN を直接指定(推奨)
  - JQUANTS_MAILADDRESS + JQUANTS_PASSWORD から自動取得

注意:
  - 無料プランはデータに遅延があります(過去データ中心)。取得データの「時点」に注意。
  - 認証情報は環境変数から読み、ログ・標準出力に出さないこと。

参考: https://jpx-jquants.com/  /  API仕様は公式ドキュメントを参照。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests が必要です: pip install -r scripts/requirements.txt")

API_BASE = "https://api.jquants.com/v1"
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


class JQuantsClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.id_token: str | None = None

    # --- 認証 ---
    def authenticate(self) -> None:
        refresh = os.environ.get("JQUANTS_REFRESH_TOKEN")
        if not refresh:
            refresh = self._get_refresh_token()
        self.id_token = self._get_id_token(refresh)

    def _get_refresh_token(self) -> str:
        mail = os.environ.get("JQUANTS_MAILADDRESS")
        pw = os.environ.get("JQUANTS_PASSWORD")
        if not (mail and pw):
            sys.exit("認証情報がありません。JQUANTS_REFRESH_TOKEN か "
                     "JQUANTS_MAILADDRESS/PASSWORD を .env に設定してください。")
        r = self.session.post(
            f"{API_BASE}/token/auth_user",
            data=json.dumps({"mailaddress": mail, "password": pw}),
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["refreshToken"]

    def _get_id_token(self, refresh_token: str) -> str:
        r = self.session.post(
            f"{API_BASE}/token/auth_refresh",
            params={"refreshtoken": refresh_token},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["idToken"]

    def _headers(self) -> dict:
        if not self.id_token:
            self.authenticate()
        return {"Authorization": f"Bearer {self.id_token}"}

    # --- エンドポイント ---
    def daily_quotes(self, code: str | None, date_from: str | None,
                     date_to: str | None) -> dict:
        params: dict[str, str] = {}
        if code:
            params["code"] = code
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        return self._get("/prices/daily_quotes", params)

    def listed_info(self, code: str | None = None) -> dict:
        params = {"code": code} if code else {}
        return self._get("/listed/info", params)

    def statements(self, code: str | None = None) -> dict:
        params = {"code": code} if code else {}
        return self._get("/fins/statements", params)

    def _get(self, path: str, params: dict) -> dict:
        r = self.session.get(f"{API_BASE}{path}", headers=self._headers(),
                             params=params, timeout=60)
        r.raise_for_status()
        return r.json()


def save_raw(payload: dict, kind: str, params: dict) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RAW_DIR / f"jquants_{kind}_{stamp}.json"
    wrapped = {
        "source": "j-quants",
        "kind": kind,
        "fetched_at": datetime.now().isoformat(),
        "params": params,
        "data": payload,
    }
    out.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="J-Quants データ取得")
    ap.add_argument("--check", action="store_true", help="認証だけ試して終了")
    ap.add_argument("--daily-quotes", action="store_true", help="日次株価を取得")
    ap.add_argument("--listed-info", action="store_true", help="銘柄情報を取得")
    ap.add_argument("--statements", action="store_true", help="財務情報を取得")
    ap.add_argument("--code", help="銘柄コード(例: 8105)")
    ap.add_argument("--from", dest="date_from", help="開始日 YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", help="終了日 YYYY-MM-DD")
    args = ap.parse_args()

    client = JQuantsClient()

    if args.check:
        client.authenticate()
        print("OK: J-Quants 認証成功(idToken 取得済み)")
        return

    if args.daily_quotes:
        params = {"code": args.code, "from": args.date_from, "to": args.date_to}
        out = save_raw(client.daily_quotes(args.code, args.date_from, args.date_to),
                       "daily_quotes", params)
    elif args.listed_info:
        out = save_raw(client.listed_info(args.code), "listed_info", {"code": args.code})
    elif args.statements:
        out = save_raw(client.statements(args.code), "statements", {"code": args.code})
    else:
        ap.print_help()
        return

    print(f"保存しました: {out}")


if __name__ == "__main__":
    main()
