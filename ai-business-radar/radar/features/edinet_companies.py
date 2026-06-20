"""Build an EDINET-code to securities-code derived map from companies raw.

The map is intentionally narrow. It reads local EDINET DB companies raw, writes
only identifiers and basic listing metadata to data/derived, and does not emit
or store provider response bodies outside the derived feature boundary.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from radar.sources import common

ROOT = Path(__file__).resolve().parent.parent.parent
PROVIDER = "edinet-db"
DATASET = "companies"
FEATURE_SET = "edinet_company_map_v1"
SCHEMA_VERSION = "1"
FEATURE_REGISTRY_VERSION = "1"
NORMALIZATION_VERSION = "1"

_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EDINET_RE = re.compile(r"^E\d{5}$")
_SEC_CODE_RE = re.compile(r"^[0-9A-Z]{4,5}$")


def _valid_asof(asof: str) -> str:
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


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


def _safe_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _edinet_code(value) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if _EDINET_RE.match(code) else None


def _sec_code(value) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if _SEC_CODE_RE.match(code) else None


def _output_dir(derived_root: Path | None, asof: str) -> Path:
    root = Path(derived_root or (ROOT / "data" / "derived"))
    if not root.is_absolute():
        root = ROOT / root
    base = (root.resolve() / "features" / FEATURE_SET / asof).resolve()
    base.mkdir(parents=True, exist_ok=True)
    if not _inside(base, root.resolve()):
        raise SystemExit("company map derived 出力先が data/derived 配下を脱出しています")
    return base


def _raw_dir(raw_dir, raw_root: Path | None) -> Path:
    root = Path(raw_root or (ROOT / "data" / "raw")).resolve()
    companies_root = (root / PROVIDER / DATASET).resolve()
    d = Path(raw_dir)
    if not d.is_absolute():
        d = ROOT / d
    d = d.resolve()
    if not _inside(d, companies_root):
        raise SystemExit("raw-dir は data/raw/edinet-db/companies 配下のみ指定できます")
    if not d.exists() or not d.is_dir():
        raise SystemExit("companies raw-dir が見つかりません")
    return d


def _code_commit() -> str:
    git = ROOT.parent / ".git"
    head = git / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref: "):
            ref = git / text.split(" ", 1)[1]
            return ref.read_text(encoding="utf-8").strip()[:12]
        return text[:12]
    except OSError:
        return "UNKNOWN"


def build_edinet_company_map(
    *,
    raw_dir,
    asof: str,
    raw_root: Path | None = None,
    derived_root: Path | None = None,
    clock=None,
) -> dict:
    """Build a derived map used to join EDINET financials with J-Quants features."""
    asof = _valid_asof(asof)
    raw_d = _raw_dir(raw_dir, raw_root)
    candidates = [
        p for p in sorted(raw_d.glob("companies_page-*.json"))
        if not p.name.endswith(".meta.json") and not p.name.endswith(".provenance.json")
    ]
    if not candidates:
        raise SystemExit("companies raw JSON がありません")

    rows_by_edinet: dict[str, dict] = {}
    input_files = []
    conflicts = []
    for raw_p in candidates:
        raw = raw_p.read_bytes()
        obj = _load_json_dict(raw_p, "companies raw")
        data = obj.get("data")
        if not isinstance(data, list):
            raise SystemExit("companies raw.data は list である必要があります")
        input_files.append({
            "path": str(raw_p),
            "raw_hash_compressed": common.hash_bytes(raw),
            "raw_hash_normalized": common.hash_bytes(common.normalize_json_bytes(raw)),
            "size": raw_p.stat().st_size,
        })
        sidecar = raw_p.with_suffix(raw_p.suffix + ".provenance.json")
        if not sidecar.exists():
            sidecar = raw_p.with_suffix(raw_p.suffix + ".meta.json")
        sidecar_meta = _load_json_dict(sidecar, "companies sidecar") if sidecar.exists() else {}
        for row in data:
            if not isinstance(row, dict):
                continue
            edinet = _edinet_code(row.get("edinet_code"))
            sec = _sec_code(row.get("sec_code") or row.get("securities_code"))
            if edinet is None:
                continue
            entry = {
                "schema_version": SCHEMA_VERSION,
                "feature_set": FEATURE_SET,
                "feature_registry_version": FEATURE_REGISTRY_VERSION,
                "asof": asof,
                "provider": PROVIDER,
                "dataset": DATASET,
                "edinet_code": edinet,
                "securities_code": sec,
                "sec_code": sec,
                "listing_status": _safe_text(row.get("listing_status")),
                "industry": _safe_text(row.get("industry")),
                "accounting_standard": _safe_text(row.get("accounting_standard")),
                "company_name": _safe_text(row.get("name_ja") or row.get("name")),
                "source": {
                    "raw_path": str(raw_p),
                    "sidecar_path": str(sidecar) if sidecar.exists() else None,
                    "retrieved_at": sidecar_meta.get("retrieved_at"),
                },
                "claim": "FACT",
            }
            if edinet in rows_by_edinet and rows_by_edinet[edinet].get("securities_code") != sec:
                conflicts.append({"edinet_code": edinet, "kept": rows_by_edinet[edinet].get("securities_code"), "seen": sec})
                continue
            rows_by_edinet[edinet] = entry

    generated = clock() if clock else datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    out_dir = _output_dir(derived_root, asof)
    companies_path = out_dir / "companies.jsonl"
    manifest_path = out_dir / "manifest.json"
    with companies_path.open("w", encoding="utf-8") as fh:
        for edinet in sorted(rows_by_edinet):
            fh.write(json.dumps(rows_by_edinet[edinet], ensure_ascii=False, sort_keys=True) + "\n")

    input_digest = common.hash_bytes(
        json.dumps(input_files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    mapped_count = sum(1 for row in rows_by_edinet.values() if row.get("securities_code"))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "feature_set": FEATURE_SET,
        "feature_registry_version": FEATURE_REGISTRY_VERSION,
        "generated_at": generated.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "asof": asof,
        "provider": PROVIDER,
        "dataset": DATASET,
        "normalization_version": NORMALIZATION_VERSION,
        "code_commit": _code_commit(),
        "raw_dir": str(raw_d),
        "input_file_count": len(input_files),
        "input_manifest_digest": input_digest,
        "row_count": len(rows_by_edinet),
        "mapped_securities_code_count": mapped_count,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "note": "EDINET code と証券コードの derived 対応表。raw本文・APIキー値は含まない。",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                             encoding="utf-8")
    return {
        "provider": PROVIDER,
        "dataset": DATASET,
        "feature_set": FEATURE_SET,
        "asof": asof,
        "row_count": len(rows_by_edinet),
        "mapped_securities_code_count": mapped_count,
        "input_file_count": len(input_files),
        "input_manifest_digest": input_digest,
        "companies_path": companies_path,
        "manifest_path": manifest_path,
        "conflict_count": len(conflicts),
    }
