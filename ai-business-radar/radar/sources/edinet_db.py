"""EDINET DB Phase B sync adapter.

Scope is intentionally narrow:
- provider=edinet-db
- dataset=companies or financials
- raw is written only under data/raw/edinet-db/<dataset>/<asof>/
- response body is never printed or returned to the CLI
- features / research_queue / evidence / LLM handoff are out of scope
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path

from . import common, live, provenance

PROVIDER = "edinet-db"
DATASET = "companies"
DATASET_FINANCIALS = "financials"
DATASETS = (DATASET, DATASET_FINANCIALS)
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 100
DEFAULT_YEARS = 1
PERIODS = ("annual", "quarterly", "quarterly_standalone")
_RETRYABLE = (429, 500, 502, 503, 504)
_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EDINET_CODE_RE = re.compile(r"^E\d{5}$")
_JST = timezone(timedelta(hours=9))


class _RequestClient:
    """Adapt live.UrllibClient(url, headers) to common.fetch(endpoint, params)."""

    def __init__(self, cfg: dict, key: str, *, http_client):
        self.cfg = cfg
        self.key = key
        self.http_client = http_client
        self.last_status = None

    def __call__(self, endpoint, params):
        url, headers = live._build_request(
            self.cfg.get("base_url", ""),
            endpoint,
            params,
            self.cfg.get("auth", "x-api-key"),
            self.key,
        )
        try:
            resp = self.http_client(url, headers)
        except Exception:
            self.last_status = None
            raise
        self.last_status = getattr(resp, "status", None)
        return resp


def _parse_iso_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError as e:
        raise SystemExit(f"datetime が不正です: {value}") from e
    if dt.tzinfo is None:
        raise SystemExit(f"datetime は timezone 付きである必要があります: {value}")
    return dt


def _asof_end_utc(asof: str) -> datetime:
    d = date.fromisoformat(_valid_asof(asof))
    return datetime.combine(d, dt_time(23, 59, 59), tzinfo=_JST).astimezone(timezone.utc)


def _valid_asof(asof: str) -> str:
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


def _provider_cfg(cfg: dict) -> tuple[dict, dict]:
    dl = cfg.get("data_layer") or {}
    pc = (dl.get("providers") or {}).get(PROVIDER)
    if not isinstance(pc, dict):
        raise SystemExit("data_layer.providers.edinet-db が config にありません")
    return dl, pc


def _endpoint_for_companies(pc: dict) -> str:
    datasets = pc.get("datasets") or {}
    if isinstance(datasets, dict):
        companies = datasets.get(DATASET) or {}
        if isinstance(companies, dict) and companies.get("path"):
            return companies["path"]
    return pc.get("ping_path", "/companies")


def _endpoint_for_financials(pc: dict, code: str) -> str:
    datasets = pc.get("datasets") or {}
    path = "/companies/{code}/financials"
    if isinstance(datasets, dict):
        financials = datasets.get(DATASET_FINANCIALS) or {}
        if isinstance(financials, dict) and financials.get("path"):
            path = financials["path"]
    return path.format(code=code)


def _positive_int(v, name: str) -> int:
    if isinstance(v, bool):
        raise SystemExit(f"{name} は正の整数で指定してください")
    try:
        n = int(v)
    except (TypeError, ValueError) as e:
        raise SystemExit(f"{name} は正の整数で指定してください") from e
    if n <= 0:
        raise SystemExit(f"{name} は正の整数で指定してください")
    return n


def _valid_edinet_code(code: str) -> str:
    if not isinstance(code, str):
        raise SystemExit("--code は EDINETコード(E02367形式)で指定してください")
    code = code.strip().upper()
    if not _EDINET_CODE_RE.match(code):
        raise SystemExit("--code は EDINETコード(E02367形式)で指定してください")
    return code


def _valid_period(period: str) -> str:
    if period not in PERIODS:
        raise SystemExit(f"--period は {PERIODS} のいずれかで指定してください")
    return period


def _raw_path(raw_root: Path, asof: str, page: int, per_page: int) -> Path:
    root = Path(raw_root).resolve()
    base = (root / PROVIDER / DATASET / asof).resolve()
    if root not in base.parents and base != root:
        raise SystemExit("raw 保存先が data/raw 配下ではありません")
    base.mkdir(parents=True, exist_ok=True)
    out = (base / f"companies_page-{page}_per-page-{per_page}.json").resolve()
    if base not in out.parents:
        raise SystemExit("raw 保存先が companies dataset 配下ではありません")
    return out


def _financials_raw_path(raw_root: Path, asof: str, code: str, period: str, years: int) -> Path:
    root = Path(raw_root).resolve()
    base = (root / PROVIDER / DATASET_FINANCIALS / asof).resolve()
    if root not in base.parents and base != root:
        raise SystemExit("raw 保存先が data/raw 配下ではありません")
    base.mkdir(parents=True, exist_ok=True)
    out = (base / f"{code}_period-{period}_years-{years}.json").resolve()
    if base not in out.parents:
        raise SystemExit("raw 保存先が financials dataset 配下ではありません")
    return out


def _parse_vendor_datetime(value) -> datetime | None:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return datetime.combine(date.fromisoformat(s), dt_time(23, 59, 59), tzinfo=_JST)
    try:
        dt = datetime.fromisoformat(s.replace(" ", "T"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_JST)
    return dt


def _financials_available_at(obj: dict, fallback: str) -> str:
    rows = obj.get("data")
    dates = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("available_at", "disclosure_date", "submit_date"):
                if (dt := _parse_vendor_datetime(row.get(key))) is not None:
                    dates.append(dt)
    if not dates:
        return fallback
    return max(dates).isoformat(timespec="seconds")


def sync_companies(
    cfg: dict,
    *,
    asof: str,
    page: int = DEFAULT_PAGE,
    per_page: int = DEFAULT_PER_PAGE,
    raw_root: Path | None = None,
    metadata_dir: Path | None = None,
    http_client=None,
    clock=None,
    sleeper=None,
    key_getter=None,
) -> dict:
    """Fetch one page of EDINET DB companies and persist raw + provenance.

    Returns only metadata/path summary. It never returns the response body.
    """
    asof = _valid_asof(asof)
    page = _positive_int(page, "--page")
    per_page = _positive_int(per_page, "--per-page")
    dl, pc = _provider_cfg(cfg)
    key_getter = key_getter or common.load_api_key
    key = key_getter(pc.get("key_var", "EDINETDB_API_KEY"))
    max_bytes = int(dl.get("max_response_bytes", live.DEFAULT_MAX_BYTES))
    retry_max = int(dl.get("retry_max", 3))
    backoff = dl.get("backoff_base_sec", 2)
    timeout = dl.get("timeout_sec", live.DEFAULT_TIMEOUT)
    http_client = http_client or live.UrllibClient(timeout, max_bytes)
    sleeper = sleeper or time.sleep
    raw_root = raw_root or (common.ROOT / "data" / "raw")
    metadata_dir = metadata_dir or provenance.default_metadata_dir()

    endpoint = _endpoint_for_companies(pc)
    params = {"page": page, "per_page": per_page}
    source_url = pc.get("base_url", "").rstrip("/") + "/" + endpoint.lstrip("/")

    adapter = _RequestClient(pc, key, http_client=http_client)
    attempt = 0
    while True:
        try:
            raw, meta_partial = common.fetch(PROVIDER, endpoint, params, client=adapter, clock=clock)
            break
        except RuntimeError as e:
            status = adapter.last_status
            if status in _RETRYABLE and attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            if status is None and attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            raise SystemExit(live._redact_with_key(str(e), key)) from e

    if len(raw) > max_bytes:
        raise SystemExit("response too large(本文は保存も表示もしない)")
    # Validate shape before writing. The parsed body is intentionally not returned.
    common.parse_json_dict(raw)

    retrieved_at = meta_partial["retrieved_at"]
    available_at = retrieved_at  # DATA_LAYER_SPEC §6: companies/listed-info are available at retrieval.
    if _parse_iso_dt(available_at) > _asof_end_utc(asof):
        raise SystemExit("available_at が asof より未来です(PIT違反・rawは保存しません)")

    meta = provenance.make_provenance(
        provider=PROVIDER,
        dataset=DATASET,
        endpoint=endpoint,
        params=params,
        retrieved_at=retrieved_at,
        raw_hash_compressed=meta_partial["raw_hash_compressed"],
        raw_hash_normalized=meta_partial["raw_hash_normalized"],
        raw_size=meta_partial["raw_size"],
        content_type="application/json",
        vendor_last_modified=None,
        available_at=available_at,
        source_url=source_url,
        license_scope="personal/local-temporary-cache/no-redistribution/no-raw-llm",
        plan_or_limit=pc.get("plan_or_limit"),
    )
    provenance.validate_provenance(meta)

    out = _raw_path(Path(raw_root), asof, page, per_page)
    out.write_bytes(raw)
    sidecar = out.with_suffix(out.suffix + ".provenance.json")
    sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance.append_fetch_log(metadata_dir, meta)

    return {
        "provider": PROVIDER,
        "dataset": DATASET,
        "asof": asof,
        "page": page,
        "per_page": per_page,
        "raw_path": out,
        "provenance_path": sidecar,
        "metadata_dir": Path(metadata_dir),
        "raw_hash_compressed": meta["raw_hash_compressed"],
        "raw_hash_normalized": meta["raw_hash_normalized"],
        "available_at": meta["available_at"],
        "attempts": attempt + 1,
    }


def sync_financials(
    cfg: dict,
    *,
    asof: str,
    code: str,
    years: int = DEFAULT_YEARS,
    period: str = "annual",
    raw_root: Path | None = None,
    metadata_dir: Path | None = None,
    http_client=None,
    clock=None,
    sleeper=None,
    key_getter=None,
) -> dict:
    """Fetch one company's financials and persist raw + provenance.

    This is still Phase B sync only: no feature generation, research queue,
    evidence rendering, or LLM handoff.
    """
    asof = _valid_asof(asof)
    code = _valid_edinet_code(code)
    years = _positive_int(years, "--years")
    period = _valid_period(period)
    dl, pc = _provider_cfg(cfg)
    key_getter = key_getter or common.load_api_key
    key = key_getter(pc.get("key_var", "EDINETDB_API_KEY"))
    max_bytes = int(dl.get("max_response_bytes", live.DEFAULT_MAX_BYTES))
    retry_max = int(dl.get("retry_max", 3))
    backoff = dl.get("backoff_base_sec", 2)
    timeout = dl.get("timeout_sec", live.DEFAULT_TIMEOUT)
    http_client = http_client or live.UrllibClient(timeout, max_bytes)
    sleeper = sleeper or time.sleep
    raw_root = raw_root or (common.ROOT / "data" / "raw")
    metadata_dir = metadata_dir or provenance.default_metadata_dir()

    endpoint = _endpoint_for_financials(pc, code)
    params = {"years": years, "period": period}
    source_url = pc.get("base_url", "").rstrip("/") + "/" + endpoint.lstrip("/")

    adapter = _RequestClient(pc, key, http_client=http_client)
    attempt = 0
    while True:
        try:
            raw, meta_partial = common.fetch(PROVIDER, endpoint, params, client=adapter, clock=clock)
            break
        except RuntimeError as e:
            status = adapter.last_status
            if status in _RETRYABLE and attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            if status is None and attempt < retry_max:
                attempt += 1
                sleeper(backoff * (2 ** (attempt - 1)))
                continue
            raise SystemExit(live._redact_with_key(str(e), key)) from e

    if len(raw) > max_bytes:
        raise SystemExit("response too large(本文は保存も表示もしない)")
    obj = common.parse_json_dict(raw)

    retrieved_at = meta_partial["retrieved_at"]
    available_at = _financials_available_at(obj, retrieved_at)
    if _parse_iso_dt(available_at).astimezone(timezone.utc) > _asof_end_utc(asof):
        raise SystemExit("financials available_at が asof より未来です(PIT違反・rawは保存しません)")

    meta = provenance.make_provenance(
        provider=PROVIDER,
        dataset=DATASET_FINANCIALS,
        endpoint=endpoint,
        params={"code": code, **params},
        retrieved_at=retrieved_at,
        raw_hash_compressed=meta_partial["raw_hash_compressed"],
        raw_hash_normalized=meta_partial["raw_hash_normalized"],
        raw_size=meta_partial["raw_size"],
        content_type="application/json",
        vendor_last_modified=None,
        available_at=available_at,
        edinet_code=code,
        source_url=source_url,
        license_scope="personal/local-temporary-cache/no-redistribution/no-raw-llm",
        plan_or_limit=pc.get("plan_or_limit"),
    )
    provenance.validate_provenance(meta)

    out = _financials_raw_path(Path(raw_root), asof, code, period, years)
    out.write_bytes(raw)
    sidecar = out.with_suffix(out.suffix + ".provenance.json")
    sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance.append_fetch_log(metadata_dir, meta)

    return {
        "provider": PROVIDER,
        "dataset": DATASET_FINANCIALS,
        "asof": asof,
        "code": code,
        "years": years,
        "period": period,
        "raw_path": out,
        "provenance_path": sidecar,
        "metadata_dir": Path(metadata_dir),
        "raw_hash_compressed": meta["raw_hash_compressed"],
        "raw_hash_normalized": meta["raw_hash_normalized"],
        "available_at": meta["available_at"],
        "attempts": attempt + 1,
    }
