"""J-Quants REST client for targeted fetches (network lives here, not in features).

Auth via env only; tokens are never printed or stored in outputs. Used by
`radar.features.jquants_rest.fetch_and_build` to fetch a few codes on demand so
Discord analysis works without a full bulk download.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse

from . import common, live

API_BASE = "https://api.jquants.com/v1"


def _drop_query(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class JQuantsRestClient:
    def __init__(self, *, timeout: int = 60, opener=None) -> None:
        self._id_token: str | None = None
        self._timeout = timeout
        self._opener = opener or live.UrllibClient(timeout=timeout)

    def _open_json(self, url: str, headers: dict | None = None, *, method: str = "GET", body: bytes | None = None) -> dict:
        headers = dict(headers or {})
        try:
            resp = self._opener(url, headers, method=method, body=body)
            status = getattr(resp, "status", None)
            if status != 200:
                raise SystemExit(common.redact(f"J-Quants REST HTTP {status}: {_drop_query(url)}"))
            return common.parse_json_dict(getattr(resp, "body", b"") or b"")
        except SystemExit:
            raise
        except urllib.error.HTTPError as e:
            safe_url = _drop_query(getattr(e, "url", "") or url)
            raise SystemExit(common.redact(f"J-Quants REST HTTP {e.code}: {safe_url}")) from e
        except urllib.error.URLError as e:
            raise SystemExit(common.redact(f"J-Quants REST network error: {e.reason}")) from e
        except Exception as e:  # noqa: BLE001
            raise SystemExit(common.redact(f"J-Quants REST error: {e}")) from e

    # --- auth (env only; never log token values) ---
    def _post_json(self, path: str, *, data: dict | None = None, params: dict | None = None) -> dict:
        url = f"{API_BASE}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        return self._open_json(url, {"Content-Type": "application/json"}, method="POST", body=body)

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
        return self._open_json(url, {"Authorization": f"Bearer {self._id_token}"})

    def daily_quotes(self, *, code: str, date_from: str | None = None, date_to: str | None = None) -> dict:
        return self._get("/prices/daily_quotes", {"code": code, "from": date_from, "to": date_to})

    def listed_info(self, *, code: str) -> dict:
        return self._get("/listed/info", {"code": code})

    def statements(self, *, code: str) -> dict:
        return self._get("/fins/statements", {"code": code})
