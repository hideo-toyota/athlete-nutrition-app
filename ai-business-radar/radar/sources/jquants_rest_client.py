"""J-Quants REST client for targeted fetches (network lives here, not in features).

Auth via env only; tokens are never printed or stored in outputs. Used by
`radar.features.jquants_rest.fetch_and_build` to fetch a few codes on demand so
Discord analysis works without a full bulk download.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API_BASE = "https://api.jquants.com/v1"


class JQuantsRestClient:
    def __init__(self, *, timeout: int = 60) -> None:
        self._id_token: str | None = None
        self._timeout = timeout

    # --- auth (env only; never log token values) ---
    def _post_json(self, path: str, *, data: dict | None = None, params: dict | None = None) -> dict:
        url = f"{API_BASE}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def authenticate(self) -> None:
        refresh = os.environ.get("JQUANTS_REFRESH_TOKEN")
        if not refresh:
            mail = os.environ.get("JQUANTS_MAILADDRESS")
            pw = os.environ.get("JQUANTS_PASSWORD")
            if not (mail and pw):
                raise SystemExit("J-Quants 認証情報がありません(.env に JQUANTS_REFRESH_TOKEN か "
                                 "JQUANTS_MAILADDRESS/PASSWORD を設定)")
            refresh = self._post_json("/token/auth_user",
                                      data={"mailaddress": mail, "password": pw})["refreshToken"]
        self._id_token = self._post_json("/token/auth_refresh", params={"refreshtoken": refresh})["idToken"]

    def _get(self, path: str, params: dict) -> dict:
        if not self._id_token:
            self.authenticate()
        url = f"{API_BASE}{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v})}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._id_token}"})
        with urllib.request.urlopen(req, timeout=self._timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def daily_quotes(self, *, code: str, date_from: str | None = None, date_to: str | None = None) -> dict:
        return self._get("/prices/daily_quotes", {"code": code, "from": date_from, "to": date_to})

    def listed_info(self, *, code: str) -> dict:
        return self._get("/listed/info", {"code": code})

    def statements(self, *, code: str) -> dict:
        return self._get("/fins/statements", {"code": code})
