"""provenance / fetch_log の schema と検証(A0)。DATA_LAYER_SPEC §5/§7 準拠。

A0 では値が未設定(None)でも key は必ず揃える。available_at は tz付き ISO8601 datetime。
書き込みは呼び出し側が渡す metadata_dir(= data/metadata)配下のみ。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

REQUIRED_FIELDS = (
    "provider", "dataset", "endpoint", "params", "schema_version", "fetch_id",
    "retrieved_at", "raw_hash_compressed", "raw_hash_normalized", "hash_algorithm",
    "normalization_version", "raw_size", "content_type", "vendor_last_modified",
    "period_end", "submit_date", "disclosure_date", "available_at",
    "entity_id", "securities_code", "edinet_code", "company_id", "isin",
    "currency", "unit", "accounting_standard", "consolidated",
    "source_doc_id", "source_url", "license_scope", "plan_or_limit",
)


def make_provenance(**fields) -> dict:
    """全必須キーを None 既定で埋めた provenance を作る。既知の既定値は補う。"""
    rec = {k: None for k in REQUIRED_FIELDS}
    rec["schema_version"] = "1"
    rec["normalization_version"] = "1"
    rec["hash_algorithm"] = "sha256"
    rec["fetch_id"] = str(uuid.uuid4())
    for k, v in fields.items():
        if k in REQUIRED_FIELDS:
            rec[k] = v
    return rec


def _is_tz_datetime(s) -> bool:
    if s is None:
        return True  # A0: 未設定可
    try:
        dt = datetime.fromisoformat(str(s))
    except (ValueError, TypeError):
        return False
    return dt.tzinfo is not None


def validate_provenance(meta: dict) -> dict:
    missing = [k for k in REQUIRED_FIELDS if k not in meta]
    if missing:
        raise SystemExit(f"provenance に必須キーが不足: {missing}")
    if not _is_tz_datetime(meta.get("available_at")):
        raise SystemExit("available_at は tz付き ISO8601 datetime である必要があります")
    if not _is_tz_datetime(meta.get("retrieved_at")):
        raise SystemExit("retrieved_at は tz付き ISO8601 datetime である必要があります")
    return meta


def append_fetch_log(metadata_dir, meta: dict) -> Path:
    """fetch_log.jsonl に追記(追記専用)。**書き込みは渡された metadata_dir 配下のみ**。"""
    validate_provenance(meta)
    d = Path(metadata_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "fetch_log.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return p
