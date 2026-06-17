"""A1 軽量疎通(connectivity only)。DATA_LAYER_SPEC §13/§14 準拠。

このモジュールは「鍵が有効で疎通できるか」だけを確認する。**それ以上はしない。**
- 取得本文(response body)を **保存しない・表示しない・Claude(LLM)に渡さない**。
- raw / data/cache / data/derived へ書かない。sync/research_queue/evidence/feature は未実装。
- 出力するのは status / provider / endpoint(path) / success / **redact 済み error** のみ。
- APIキー値は header/url の中だけに置き、ログ・例外・戻り値・テスト出力に一切残さない。
- 実 HTTP は注入可能(既定 urllib・stdlib のみ)。テストは fake client。

⚠️ ToS: A1 は「疎通のみ」。**分析利用・第三者LLM投入ではない。** B(sync=raw保存)と
第三者LLM入力は LICENSE_MATRIX の ToS 確認まで引き続き NO-GO(本モジュールは何も保存しない)。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from urllib.parse import urlencode

from . import common

DEFAULT_TIMEOUT = 10
DEFAULT_MAX_BYTES = 1_048_576
_RETRYABLE = (429, 500, 502, 503, 504)
PROVIDERS = ("jquants", "edinet-db")


class Resp:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body


class UrllibClient:
    """実 HTTP(stdlib urllib)。本文は max_bytes まで読み、保存も返却もしない用途。

    呼び出し: client(url, headers) -> Resp(status, body)。
    HTTPError(401/403/429/5xx) は Resp(status) に変換。URLError/timeout は送出(呼び出し側で redact)。
    """

    def __init__(self, timeout=DEFAULT_TIMEOUT, max_bytes=DEFAULT_MAX_BYTES):
        self.timeout = timeout
        self.max_bytes = max_bytes

    def __call__(self, url, headers):  # pragma: no cover - 実ネットワークはテスト対象外
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read(self.max_bytes + 1)
                return Resp(getattr(r, "status", 200) or 200, body)
        except urllib.error.HTTPError as e:
            return Resp(e.code, b"")  # 本文は読まない(キー/個票を残さない)


def _provider_cfg(cfg: dict, provider: str):
    dl = cfg.get("data_layer") or {}
    pc = (dl.get("providers") or {}).get(provider)
    if not pc:
        raise SystemExit(f"data_layer.providers.{provider} が config にありません(設定してください)")
    return dl, pc


def _build_request(base_url: str, path: str, params, auth: str, key: str):
    """url + headers を組み立てる。**キーは header/query の中だけ**(path・ログには出さない)。"""
    url = base_url.rstrip("/") + "/" + str(path).lstrip("/")
    headers = {"Accept": "application/json", "User-Agent": "ai-business-radar/A1-connectivity"}
    q = dict(params or {})
    if auth == "bearer":
        headers["Authorization"] = "Bearer " + key
    elif auth == "x-api-key":
        headers["X-API-Key"] = key
    elif auth.startswith("header:"):
        headers[auth.split(":", 1)[1]] = key
    elif auth.startswith("query:"):
        q[auth.split(":", 1)[1]] = key
    else:
        raise SystemExit(f"未知の auth 方式: {auth}(bearer|x-api-key|header:NAME|query:NAME)")
    if q:
        url = url + "?" + urlencode(q)
    return url, headers


def ping(provider: str, cfg: dict, *, client=None, clock=None, sleeper=None, key_getter=None) -> dict:
    """軽量疎通。鍵を読み(値は出さない)、最小 endpoint に1回 GET し、可否だけ返す。

    返り値(本文は含めない): {provider, endpoint, status, success, error(redact), retrieved_at, attempts}。
    429/5xx/ネットワーク失敗は retry_max まで指数バックオフ。401/403 は即時失敗(再試行しない)。
    """
    if provider not in PROVIDERS:
        raise SystemExit(f"provider は {PROVIDERS} のいずれか: {provider!r}")
    dl, pc = _provider_cfg(cfg, provider)
    key_getter = key_getter or common.load_api_key
    key = key_getter(pc.get("key_var", ""))  # 未設定は SystemExit(値は表示しない)
    timeout = dl.get("timeout_sec", DEFAULT_TIMEOUT)
    max_bytes = int(dl.get("max_response_bytes", DEFAULT_MAX_BYTES))
    retry_max = int(dl.get("retry_max", 3))
    backoff = dl.get("backoff_base_sec", 2)
    client = client or UrllibClient(timeout, max_bytes)
    sleeper = sleeper or time.sleep

    path = pc.get("ping_path", "/")
    url, headers = _build_request(pc.get("base_url", ""), path,
                                  pc.get("ping_params"), pc.get("auth", "bearer"), key)

    status = None
    success = False
    error = None
    attempt = 0
    while True:
        try:
            resp = client(url, headers)
            status = getattr(resp, "status", None)
            body = getattr(resp, "body", b"") or b""
            if status == 200:
                if len(body) > max_bytes:
                    error = "response too large(本文は保存も表示もしない)"
                else:
                    # 形だけ確認(本文の中身は保存も表示もしない)。非dict/壊れJSONは error。
                    try:
                        obj = json.loads(body) if body else None
                    except ValueError:
                        obj = None
                        error = "response が有効な JSON ではありません"
                    if isinstance(obj, dict):
                        success = True
                    elif error is None:
                        error = "response の root が JSON object ではありません"
                break
            if status in _RETRYABLE and attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            error = f"HTTP {status}"
            break
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001  ネットワーク失敗/timeout。キーを残さない
            if attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            error = f"network error: {e}"
            break

    return {
        "provider": provider,
        "endpoint": path,                       # path のみ(キー・query秘匿値を含めない)
        "status": status,
        "success": bool(success and error is None),
        "error": common.redact(error) if error else None,
        "retrieved_at": common.utcnow_iso(clock),
        "attempts": attempt + 1,
    }
