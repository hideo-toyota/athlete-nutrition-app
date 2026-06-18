"""Build derived feature files from EDINET DB financials raw + provenance."""
from __future__ import annotations

import json
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from radar.sources import common

from .compute import compute_financial_features
from .registry import (
    FEATURE_REGISTRY_VERSION,
    FEATURE_SET,
    NORMALIZATION_VERSION,
    SCHEMA_VERSION,
    registry_fingerprint_payload,
)

ROOT = Path(__file__).resolve().parent.parent.parent
PROVIDER = "edinet-db"
DATASET = "financials"
_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EDINET_RE = re.compile(r"^E\d{5}$")
_JST = timezone(timedelta(hours=9))


def _valid_asof(asof: str) -> str:
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


def _parse_tz_dt(value, field: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as e:
        raise SystemExit(f"{field} は tz付き ISO8601 datetime である必要があります") from e
    if dt.tzinfo is None:
        raise SystemExit(f"{field} は timezone 付きである必要があります")
    return dt


def _asof_end(asof: str) -> datetime:
    d = date.fromisoformat(_valid_asof(asof))
    return datetime.combine(d, time(23, 59, 59), tzinfo=_JST)


def _inside(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _load_json_dict(path: Path, what: str) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{what} の JSON が不正です: {e}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"{what} の root は object である必要があります")
    return obj


def _edinet_code(value) -> str:
    if not isinstance(value, str):
        raise SystemExit("provenance.edinet_code がありません")
    code = value.strip().upper()
    if not _EDINET_RE.match(code):
        raise SystemExit("provenance.edinet_code は E02367 形式である必要があります")
    return code


def _code_commit() -> str:
    git = ROOT.parent / ".git"
    head = git / "HEAD"
    try:
        txt = head.read_text(encoding="utf-8").strip()
        if txt.startswith("ref: "):
            ref = git / txt.split(" ", 1)[1]
            return ref.read_text(encoding="utf-8").strip()[:12]
        return txt[:12]
    except OSError:
        return "UNKNOWN"


def _config_hash() -> str:
    payload = registry_fingerprint_payload()
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return common.hash_bytes(raw)


def _output_path(derived_root: Path, asof: str, code: str) -> Path:
    root = Path(derived_root).resolve()
    base = (root / "features" / FEATURE_SET / asof).resolve()
    base.mkdir(parents=True, exist_ok=True)
    out = (base / f"{code}.json").resolve()
    if not _inside(out, base):
        raise SystemExit("derived 出力先が features 配下を脱出しています")
    return out


def build_financial_features(
    *,
    raw_path,
    asof: str,
    raw_root: Path | None = None,
    derived_root: Path | None = None,
    clock=None,
) -> dict:
    """Build one derived feature JSON from an explicit financials raw path."""
    asof = _valid_asof(asof)
    raw_root = (raw_root or (ROOT / "data" / "raw")).resolve()
    financials_root = (raw_root / PROVIDER / DATASET).resolve()
    raw_p = Path(raw_path)
    if not raw_p.is_absolute():
        raw_p = ROOT / raw_p
    raw_p = raw_p.resolve()
    if not _inside(raw_p, financials_root):
        raise SystemExit("raw-path は data/raw/edinet-db/financials 配下のみ指定できます")
    if not raw_p.exists():
        raise SystemExit(f"raw-path が見つかりません: {raw_p}")

    sidecar = raw_p.with_suffix(raw_p.suffix + ".provenance.json")
    if not sidecar.exists():
        raise SystemExit(f"provenance sidecar が見つかりません: {sidecar}")
    meta = _load_json_dict(sidecar, "provenance")
    if meta.get("provider") != PROVIDER or meta.get("dataset") != DATASET:
        raise SystemExit("provenance provider/dataset が edinet-db/financials ではありません")
    code = _edinet_code(meta.get("edinet_code"))

    available_at = _parse_tz_dt(meta.get("available_at"), "available_at")
    if available_at > _asof_end(asof):
        raise SystemExit("available_at が asof より未来です(PIT違反・derivedは書きません)")

    raw = raw_p.read_bytes()
    compressed = common.hash_bytes(raw)
    normalized = common.hash_bytes(common.normalize_json_bytes(raw))
    if compressed != meta.get("raw_hash_compressed"):
        raise SystemExit("raw_hash_compressed が provenance と一致しません")
    if normalized != meta.get("raw_hash_normalized"):
        raise SystemExit("raw_hash_normalized が provenance と一致しません")

    raw_obj = _load_json_dict(raw_p, "raw")
    hashes = {"raw_hash_compressed": compressed, "raw_hash_normalized": normalized}
    computed = compute_financial_features(raw_obj, raw_hashes=hashes)
    features = computed["features"]
    unknown_count = sum(1 for f in features.values() if f.get("status") == "UNKNOWN")
    generated = clock() if clock else datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)

    derived_root = derived_root or (ROOT / "data" / "derived")
    out = _output_path(Path(derived_root), asof, code)
    doc = {
        "schema_version": SCHEMA_VERSION,
        "feature_set": FEATURE_SET,
        "feature_registry_version": FEATURE_REGISTRY_VERSION,
        "generated_at": generated.isoformat(timespec="seconds"),
        "asof": asof,
        "provider": PROVIDER,
        "dataset": DATASET,
        "edinet_code": code,
        "period": (meta.get("params") or {}).get("period", "annual"),
        "input": {
            "raw_path": str(raw_p),
            "provenance_path": str(sidecar),
            "raw_hash_normalized": normalized,
            "raw_hash_compressed": compressed,
            "available_at": meta.get("available_at"),
            "retrieved_at": meta.get("retrieved_at"),
        },
        "build": {
            "config_hash": _config_hash(),
            "code_commit": _code_commit(),
            "normalization_version": NORMALIZATION_VERSION,
        },
        "source_snapshot": computed["source_snapshot"],
        "restatement_flags": computed["restatement_flags"],
        "features": features,
    }
    out.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {
        "provider": PROVIDER,
        "dataset": DATASET,
        "asof": asof,
        "edinet_code": code,
        "feature_set": FEATURE_SET,
        "feature_count": len(features),
        "unknown_count": unknown_count,
        "raw_hash_compressed": compressed,
        "raw_hash_normalized": normalized,
        "output_path": out,
    }
