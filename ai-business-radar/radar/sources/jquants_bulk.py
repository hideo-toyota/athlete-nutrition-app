"""J-Quants Premium Bulk sync(raw download only).

Scope:
- J-Quants Bulk list/get only.
- Writes raw gzip files under data/raw/jquants/bulk/<provider-key>.
- Writes metadata manifests under data/metadata.
- Does not print API key values, download URLs, or provider response bodies.
- Does not build features, research queues, evidence, rankings, or advice.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import common

ROOT = Path(__file__).resolve().parent.parent.parent
PROVIDER = "jquants"
RAW_ROOT = ROOT / "data" / "raw" / "jquants" / "bulk"
META_ROOT = ROOT / "data" / "metadata"

DEFAULT_BULK_ENDPOINTS = (
    "/equities/master",
    "/equities/bars/daily",
    "/fins/summary",
    "/fins/dividend",
)


def _provider_cfg(cfg: dict) -> tuple[dict, dict]:
    dl = cfg.get("data_layer") or {}
    pc = (dl.get("providers") or {}).get(PROVIDER)
    if not isinstance(pc, dict):
        raise SystemExit("data_layer.providers.jquants が config にありません")
    return dl, pc


def _endpoint(endpoint: str) -> str:
    text = str(endpoint or "").strip()
    if not text.startswith("/") or any(part in {"", ".", ".."} for part in text.split("/")[1:]):
        raise SystemExit(f"J-Quants bulk endpoint が不正です: {endpoint}")
    return text


def _safe_key_path(key_name: str, *, raw_root: Path = RAW_ROOT) -> Path:
    if not isinstance(key_name, str) or not key_name:
        raise RuntimeError("bulk file key が空です")
    parts = key_name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RuntimeError("unsafe bulk file key")
    dest = raw_root.joinpath(*parts).resolve()
    base = raw_root.resolve()
    try:
        dest.relative_to(base)
    except ValueError as e:
        raise RuntimeError("bulk raw path escapes data/raw/jquants/bulk") from e
    return dest


def _headers(key: str) -> dict:
    return {
        "Accept": "application/json",
        "User-Agent": "ai-business-radar/jquants-bulk",
        "X-API-Key": key,
    }


def _url(base_url: str, path: str, params: dict) -> str:
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return url


def _request_json(url: str, headers: dict, *, timeout: float, max_bytes: int) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # pragma: no cover - live network
            raw = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason.__class__.__name__}")
    if len(raw) > max_bytes:
        raise RuntimeError("response too large")
    try:
        obj = json.loads(raw)
    except ValueError as e:
        raise RuntimeError(f"JSON parse error: {e.__class__.__name__}")
    if not isinstance(obj, dict):
        raise RuntimeError("JSON root is not object")
    return obj


def _download_url(obj: dict) -> str:
    candidates = [
        obj.get("url"),
        obj.get("URL"),
        obj.get("download_url"),
        obj.get("downloadUrl"),
    ]
    data = obj.get("data")
    if isinstance(data, dict):
        candidates.extend([
            data.get("url"),
            data.get("URL"),
            data.get("download_url"),
            data.get("downloadUrl"),
        ])
    for c in candidates:
        if isinstance(c, str) and c.startswith("http"):
            return c
    raise RuntimeError("bulk/get did not return a download URL")


def _redact_with_key(text, key: str) -> str:
    redacted = common.redact(text)
    quoted = urllib.parse.quote(key, safe="") if key else ""
    quoted_plus = urllib.parse.quote_plus(key) if key else ""
    for secret in {key, quoted, quoted_plus}:
        if secret:
            redacted = redacted.replace(secret, "***REDACTED***")
    return redacted


def _download_file(url: str, dest: Path, *, timeout: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp, tmp.open("wb") as fh:  # pragma: no cover - live network
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
        tmp.replace(dest)
    except Exception:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def _hash_gzip_payload(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with gzip.open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _normalize_row(endpoint: str, row: dict) -> dict | None:
    if not isinstance(row, dict) or not row.get("Key"):
        return None
    size = row.get("Size")
    try:
        size = int(size) if size is not None else None
    except (TypeError, ValueError):
        size = None
    return {
        "endpoint": endpoint,
        "key": str(row["Key"]),
        "last_modified": row.get("LastModified"),
        "size": size,
    }


def _maybe_sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def fetch_bulk(
    cfg: dict,
    *,
    endpoints: list[str] | None = None,
    date_filter: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    download: bool = False,
    max_files: int | None = None,
    sleep_sec: float = 0.05,
    key_getter=None,
    json_getter=None,
    file_downloader=None,
    clock=None,
    raw_root: Path = RAW_ROOT,
    meta_root: Path = META_ROOT,
) -> dict:
    """List/download J-Quants Bulk files.

    `json_getter(url, headers, timeout=..., max_bytes=...) -> dict` and
    `file_downloader(url, dest, timeout=...)` are injectable for offline tests.
    """
    dl, pc = _provider_cfg(cfg)
    key_getter = key_getter or common.load_api_key
    key = key_getter(pc.get("key_var", "JQUANTS_API_KEY"))
    base_url = str(pc.get("base_url") or "").rstrip("/")
    if not base_url:
        raise SystemExit("data_layer.providers.jquants.base_url が未設定です")
    timeout = float(dl.get("timeout_sec", 10))
    max_bytes = int(dl.get("max_response_bytes", 1_048_576))
    json_getter = json_getter or _request_json
    file_downloader = file_downloader or _download_file
    if endpoints is None:
        endpoints = [] if date_filter else list(DEFAULT_BULK_ENDPOINTS)
    endpoints = [_endpoint(e) for e in endpoints]
    if date_filter and (from_date or to_date):
        raise SystemExit("--date と --from/--to は同時指定できません")
    if date_filter and endpoints:
        raise SystemExit("--date は全endpointの日付指定です。--endpoint と併用せず、endpoint単位では --from/--to を使ってください")
    if (from_date and not to_date) or (to_date and not from_date):
        raise SystemExit("--from と --to はセットで指定してください")
    if max_files is not None and max_files <= 0:
        raise SystemExit("--max-files は正の整数で指定してください")

    now = clock() if clock else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    stamp = now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started_at = now.astimezone(timezone.utc).isoformat(timespec="seconds")
    headers = _headers(key)

    rows: list[dict] = []
    errors: list[dict] = []
    endpoint_summaries: list[dict] = []
    query_specs: list[tuple[str, dict[str, str]]]
    if date_filter:
        query_specs = [(f"date:{date_filter}", {"date": date_filter})]
    else:
        query_specs = [(endpoint, {"endpoint": endpoint}) for endpoint in endpoints]

    for endpoint, params in query_specs:
        if from_date and to_date:
            params["from"] = from_date
            params["to"] = to_date
        try:
            obj = json_getter(_url(base_url, "/bulk/list", params), headers, timeout=timeout, max_bytes=max_bytes)
            data = obj.get("data")
            if not isinstance(data, list):
                raise RuntimeError("bulk/list returned no data list")
            ep_rows = [r for r in (_normalize_row(endpoint, row) for row in data) if r is not None]
            rows.extend(ep_rows)
            endpoint_summaries.append({
                "endpoint": endpoint,
                "file_count": len(ep_rows),
                "size_bytes": sum(int(r.get("size") or 0) for r in ep_rows),
            })
        except Exception as e:  # noqa: BLE001
            errors.append({"endpoint": endpoint, "error": _redact_with_key(str(e), key)})
        _maybe_sleep(sleep_sec)

    if max_files is not None:
        rows = rows[:max_files]

    downloaded: list[dict] = []
    if download:
        for row in rows:
            key_name = row["key"]
            dest = _safe_key_path(key_name, raw_root=raw_root)
            expected_size = row.get("size")
            if dest.exists() and (expected_size is None or dest.stat().st_size == expected_size):
                downloaded.append({
                    **row,
                    "path": str(dest.relative_to(ROOT)) if dest.is_relative_to(ROOT) else str(dest),
                    "status": "skipped_existing",
                    "raw_hash_compressed": common.hash_bytes(dest.read_bytes()),
                    "raw_hash_uncompressed": _hash_gzip_payload(dest),
                })
                continue
            try:
                obj = json_getter(
                    _url(base_url, "/bulk/get", {"key": key_name}),
                    headers,
                    timeout=timeout,
                    max_bytes=max_bytes,
                )
                url = _download_url(obj)
                file_downloader(url, dest, timeout=timeout)
                downloaded.append({
                    **row,
                    "path": str(dest.relative_to(ROOT)) if dest.is_relative_to(ROOT) else str(dest),
                    "status": "downloaded",
                    "raw_hash_compressed": common.hash_bytes(dest.read_bytes()),
                    "raw_hash_uncompressed": _hash_gzip_payload(dest),
                })
            except Exception as e:  # noqa: BLE001
                errors.append({"key": key_name, "error": _redact_with_key(str(e), key)})
            _maybe_sleep(sleep_sec)

    manifest = {
        "provider": PROVIDER,
        "mode": "bulk_download" if download else "bulk_list",
        "started_at": started_at,
        "endpoints": endpoint_summaries,
        "date": date_filter,
        "from": from_date,
        "to": to_date,
        "total_files": len(rows),
        "total_size_bytes": sum(int(r.get("size") or 0) for r in rows),
        "downloaded_count": sum(1 for r in downloaded if r.get("status") == "downloaded"),
        "skipped_existing_count": sum(1 for r in downloaded if r.get("status") == "skipped_existing"),
        "errors": errors,
        "files": rows,
        "downloaded_files": downloaded,
        "raw_root": str(raw_root.relative_to(ROOT)) if raw_root.is_relative_to(ROOT) else str(raw_root),
        "plan_or_limit": pc.get("plan_or_limit"),
    }
    kind = "download" if download else "list"
    manifest_path = meta_root / f"jquants_bulk_{kind}_{stamp}.json"
    _write_json(manifest_path, manifest)
    manifest["manifest_path"] = manifest_path
    return manifest
