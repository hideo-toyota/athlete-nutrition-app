"""source 層の共通骨格(A0: ネットワーク無し)。

- env からキーを読む(未設定は SystemExit・値は表示しない)
- redact(既知キー値 / Authorization / Bearer をマスク)
- HTTP client / clock を注入できる fetch 骨格(既定 client は接続せず停止)
- hash(圧縮元 / 正規化後)・JSON検証

⚠️ A0 では実ネットワーク client を持たない。外部URLへは接続しない。実 client は A1。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
_ENV = ROOT / ".env"
KEY_VARS = (
    "JQUANTS_API_KEY",
    "EDINETDB_API_KEY",
    "JQUANTS_REFRESH_TOKEN",
    "JQUANTS_MAILADDRESS",
    "JQUANTS_PASSWORD",
    "JQUANTS_ID_TOKEN",
)


def _load_dotenv() -> None:
    """.env があれば os.environ に読み込む(既存値は上書きしない)。値はログに出さない。"""
    if not _ENV.exists():
        return
    for line in _ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def load_api_key(name: str) -> str:
    """env からキーを取得。未設定は停止(**値はメッセージに含めない**)。"""
    _load_dotenv()
    val = os.environ.get(name, "")
    if not val:
        raise SystemExit(f"{name} が未設定です(.env に設定してください)。※キー値はここには表示しません。")
    return val


def _known_secrets() -> list[str]:
    _load_dotenv()
    vals = [v for k in KEY_VARS if (v := os.environ.get(k))]
    return sorted(set(vals), key=len, reverse=True)


def redact(text) -> str:
    """既知のAPIキー値・各種クレデンシャル表現をマスクする(漏洩防止・多重適用OK)。"""
    if not isinstance(text, str):
        text = str(text)
    for sec in _known_secrets():
        text = text.replace(sec, "***REDACTED***")
    field = (
        r"(?:x-api-key|api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"refreshtoken|id[_-]?token|idtoken|token|secret|password|mailaddress)"
    )
    # JSON / dict / header-like fields: "api_key":"...", 'X-API-Key': '...', key=...
    text = re.sub(
        rf"(?i)([\"']?{field}[\"']?\s*[:=]\s*[\"']?)[^\"',}}\]\s]+",
        r"\1***REDACTED***",
        text,
    )
    # Authorization can contain a scheme plus a token; stop at quote/comma/bracket boundary.
    text = re.sub(
        r"(?i)([\"']?authorization[\"']?\s*[:=]\s*[\"']?)(?:bearer|basic|token)?\s*[^\"',}\]\s]+",
        r"\1***REDACTED***",
        text,
    )
    # URL クエリ: api_key/token/refreshtoken/key/secret/password 等
    text = re.sub(r"(?i)([?&](?:api[_-]?key|access[_-]?token|refresh[_-]?token|refreshtoken|id[_-]?token|idtoken|token|key|secret|password)=)[^&\s]+",
                  r"\1***REDACTED***", text)
    # 裸の Bearer トークン
    text = re.sub(r"(?i)\bbearer\s+\S+", "bearer ***REDACTED***", text)
    return text


def require_jquants_personal_use_confirmed(cfg: dict, *, operation: str) -> None:
    """J-Quants raw/derived entrypoint gate.

    Missing is treated as False so new environments cannot accidentally sync/build
    paid-provider data without an explicit personal-use confirmation in config.
    """
    pc = (((cfg or {}).get("data_layer") or {}).get("providers") or {}).get("jquants") or {}
    if pc.get("tos_personal_use_confirmed") is not True:
        raise SystemExit(
            f"J-Quants {operation} は config.data_layer.providers.jquants."
            "tos_personal_use_confirmed=true が必要です。"
            "個人利用・raw非公開・再配布禁止・手動purge方針を確認してから有効化してください。"
        )


def utcnow_iso(clock=None) -> str:
    now = clock() if clock else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.isoformat(timespec="seconds")


def hash_bytes(b) -> str:
    if isinstance(b, str):
        b = b.encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def normalize_json_bytes(b) -> bytes:
    """JSONとして解釈できれば sort_keys で正規化。できなければ素のバイト列。"""
    try:
        obj = json.loads(b)
    except (ValueError, TypeError):
        return b if isinstance(b, bytes) else str(b).encode("utf-8")
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def parse_json_dict(raw) -> dict:
    """レスポンスを dict として解釈。壊れJSON・非dict root は停止(値はredact)。"""
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError) as e:
        raise SystemExit(redact(f"JSON parse error: {e}"))
    if not isinstance(obj, dict):
        raise SystemExit("レスポンスの root が object ではありません")
    return obj


class NoNetworkClient:
    """A0 既定 client。呼ばれたら停止(=既定で外部接続しないことを保証)。"""

    def __call__(self, *args, **kwargs):
        raise SystemExit("A0: 実ネットワークは未実装です。fetch に fake/実 client を注入してください(実疎通は A1)。")


def fetch(provider, endpoint, params, *, client=None, clock=None):
    """注入された client を呼ぶだけの骨格。

    client(endpoint, params) -> resp(status:int, body:bytes)。
    A0 既定 client は接続せず停止する。例外・非200にキー値は残さない(redact)。
    返り値: (raw_bytes, meta_partial)。完全な provenance は provenance.make_provenance で補完。
    """
    client = client or NoNetworkClient()
    try:
        resp = client(endpoint, params)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001  例外にキーを残さない
        raise RuntimeError(redact(str(e)))
    status = getattr(resp, "status", None)
    body = getattr(resp, "body", b"")
    if status != 200:
        raise RuntimeError(redact(f"HTTP {status} from {provider}:{endpoint}"))
    raw = body if isinstance(body, bytes) else str(body).encode("utf-8")
    meta = {
        "provider": provider, "endpoint": endpoint, "params": params,
        "retrieved_at": utcnow_iso(clock),
        "raw_hash_compressed": hash_bytes(raw),
        "raw_hash_normalized": hash_bytes(normalize_json_bytes(raw)),
        "hash_algorithm": "sha256", "raw_size": len(raw),
    }
    return raw, meta
