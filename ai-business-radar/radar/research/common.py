"""Shared helpers for local-only research artifacts."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from radar.features.registry import FEATURE_SET

ROOT = Path(__file__).resolve().parent.parent.parent
JQUANTS_FEATURE_SET = "jquants_equity_v1"
EDINET_COMPANY_MAP_FEATURE_SET = "edinet_company_map_v1"
_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EDINET_RE = re.compile(r"^E\d{5}$")
_SECURITIES_CODE_RE = re.compile(r"^[0-9A-Z]{4,5}$")

FORBIDDEN_OUTPUT_TOKENS = (
    "buy_candidate",
    "recommendation",
    "expected_return",
    "期待リターン",
    "ランキング",
    "おすすめ",
    "買うべき",
    "上がる可能性が高い",
)

DISCLAIMER = (
    "これは調査用の整理であり、投資助言・売買指示・利益保証・将来予測ではありません。"
    "売買を考える場合も discipline check と人間判断が必要です。"
)


def valid_asof(asof: str | None) -> str | None:
    if asof is None:
        return None
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


def valid_edinet_code(code: str) -> str:
    if not isinstance(code, str):
        raise SystemExit("Phase D0 evidence は EDINETコード(E02367形式)のみ対応")
    code = code.strip().upper()
    if not _EDINET_RE.match(code):
        raise SystemExit("Phase D0 evidence は EDINETコード(E02367形式)のみ対応")
    return code


def feature_root(derived_root: Path | None = None) -> Path:
    return (derived_root or (ROOT / "data" / "derived")) / "features" / FEATURE_SET


def _feature_root(feature_set: str, derived_root: Path | None = None) -> Path:
    return (derived_root or (ROOT / "data" / "derived")) / "features" / feature_set


def latest_asof(root: Path) -> str:
    if not root.exists():
        raise SystemExit(f"derived feature directory が見つかりません: {root}")
    dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and _ASOF_RE.match(p.name))
    if not dirs:
        raise SystemExit(f"derived feature asof directory がありません: {root}")
    return dirs[-1]


def latest_asof_at_or_before(root: Path, asof: str | None = None) -> str | None:
    if not root.exists():
        return None
    limit = valid_asof(asof) if asof is not None else None
    dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and _ASOF_RE.match(p.name))
    if limit is not None:
        dirs = [d for d in dirs if d <= limit]
    return dirs[-1] if dirs else None


def load_feature_docs(*, asof: str | None = None, derived_root: Path | None = None) -> tuple[str, list[dict]]:
    root = feature_root(derived_root)
    asof = valid_asof(asof) or latest_asof(root)
    d = root / asof
    if not d.exists():
        raise SystemExit(f"derived feature asof directory が見つかりません: {d}")
    docs = []
    for p in sorted(d.glob("E*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise SystemExit(f"derived feature JSON が不正です({p}): {e}") from e
        if not isinstance(obj, dict):
            raise SystemExit(f"derived feature root は object である必要があります: {p}")
        if obj.get("feature_set") != FEATURE_SET:
            raise SystemExit(f"feature_set が違います: {p}")
        obj["_path"] = p
        docs.append(obj)
    if not docs:
        raise SystemExit(f"derived feature JSON がありません: {d}")
    return asof, docs


def load_feature_doc(entity: str, *, asof: str | None = None, derived_root: Path | None = None) -> tuple[str, dict]:
    code = valid_edinet_code(entity)
    root = feature_root(derived_root)
    asof = valid_asof(asof) or latest_asof(root)
    p = root / asof / f"{code}.json"
    if not p.exists():
        raise SystemExit(f"derived feature が見つかりません: {p}")
    obj = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit(f"derived feature root は object である必要があります: {p}")
    obj["_path"] = p
    return asof, obj


def _load_json(path: Path, what: str) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{what} の JSON が不正です({path}): {e}") from e
    if not isinstance(obj, dict):
        raise SystemExit(f"{what} の root は object である必要があります: {path}")
    return obj


def normalize_securities_code(value) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    if not _SECURITIES_CODE_RE.match(code):
        return None
    return code


def securities_code_candidates(value) -> list[str]:
    code = normalize_securities_code(value)
    if code is None:
        return []
    out = [code]
    if len(code) == 4:
        out.append(code + "0")
    elif len(code) == 5 and code.endswith("0"):
        out.append(code[:4])
    return out


def load_edinet_company_map(*, asof: str | None = None, derived_root: Path | None = None) -> dict:
    """Load optional EDINET code -> securities code map from derived data."""
    root = _feature_root(EDINET_COMPANY_MAP_FEATURE_SET, derived_root)
    selected = latest_asof_at_or_before(root, asof)
    if selected is None:
        return {"asof": None, "by_edinet": {}, "path": None}
    p = root / selected / "companies.jsonl"
    if not p.exists():
        return {"asof": selected, "by_edinet": {}, "path": p}
    by_edinet = {}
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise SystemExit(f"company map JSONL が不正です({p}:{lineno}): {e}") from e
        if not isinstance(obj, dict):
            raise SystemExit(f"company map root は object である必要があります({p}:{lineno})")
        if obj.get("feature_set") != EDINET_COMPANY_MAP_FEATURE_SET:
            raise SystemExit(f"company map feature_set が違います({p}:{lineno})")
        code = obj.get("edinet_code")
        if isinstance(code, str) and _EDINET_RE.match(code):
            by_edinet[code] = obj
    return {"asof": selected, "by_edinet": by_edinet, "path": p}


def load_jquants_context(*, asof: str | None = None, derived_root: Path | None = None) -> dict:
    """Load optional J-Quants derived market features without exposing raw input."""
    root = _feature_root(JQUANTS_FEATURE_SET, derived_root)
    selected = latest_asof_at_or_before(root, asof)
    if selected is None:
        return {"asof": None, "by_code": {}, "manifest": None, "features_path": None, "manifest_path": None}
    d = root / selected
    features_path = d / "features.jsonl"
    by_code = {}
    if features_path.exists():
        for lineno, line in enumerate(features_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"J-Quants features JSONL が不正です({features_path}:{lineno}): {e}") from e
            if not isinstance(obj, dict):
                raise SystemExit(f"J-Quants feature root は object である必要があります({features_path}:{lineno})")
            if obj.get("feature_set") != JQUANTS_FEATURE_SET:
                raise SystemExit(f"J-Quants feature_set が違います({features_path}:{lineno})")
            code = normalize_securities_code(obj.get("securities_code"))
            if code:
                by_code[code] = obj
                for alias in securities_code_candidates(code):
                    by_code.setdefault(alias, obj)
    manifest_path = d / "manifest.json"
    manifest = _load_json(manifest_path, "J-Quants manifest") if manifest_path.exists() else None
    if manifest is not None and manifest.get("feature_set") != JQUANTS_FEATURE_SET:
        raise SystemExit(f"J-Quants manifest feature_set が違います: {manifest_path}")
    return {
        "asof": selected,
        "by_code": by_code,
        "manifest": manifest,
        "features_path": features_path if features_path.exists() else None,
        "manifest_path": manifest_path if manifest_path.exists() else None,
    }


def _doc_securities_candidates(doc: dict, company_map: dict | None = None) -> list[str]:
    entity = doc.get("entity") if isinstance(doc.get("entity"), dict) else {}
    input_meta = doc.get("input") if isinstance(doc.get("input"), dict) else {}
    values = [
        doc.get("securities_code"),
        doc.get("sec_code"),
        entity.get("securities_code"),
        entity.get("sec_code"),
        input_meta.get("securities_code"),
        input_meta.get("sec_code"),
    ]
    code = doc.get("edinet_code")
    if company_map and isinstance(code, str):
        mapped = (company_map.get("by_edinet") or {}).get(code) or {}
        values.extend([mapped.get("securities_code"), mapped.get("sec_code")])
    out = []
    seen = set()
    for value in values:
        for candidate in securities_code_candidates(value):
            if candidate not in seen:
                out.append(candidate)
                seen.add(candidate)
    return out


_JQUANTS_CONTEXT_FEATURES = (
    "latest_close",
    "latest_volume",
    "return_20d",
    "return_60d",
    "return_252d",
    "per_trailing",
    "pbr",
    "eps_trailing",
    "bps",
    "sales_growth_yoy",
    "operating_margin",
    "net_margin",
    "roe_proxy",
    "equity_ratio",
    "dividend_record_present",
)


def jquants_market_context(doc: dict, *, jquants: dict | None = None, company_map: dict | None = None) -> dict:
    jquants = jquants or {"by_code": {}}
    by_code = jquants.get("by_code") or {}
    for code in _doc_securities_candidates(doc, company_map):
        jq = by_code.get(code)
        if jq:
            features = jq.get("features") or {}
            return {
                "status": "matched",
                "feature_set": jq.get("feature_set"),
                "jquants_asof": jquants.get("asof"),
                "company_map_asof": (company_map or {}).get("asof"),
                "securities_code": jq.get("securities_code") or code,
                "latest_price_date": (jq.get("source_dates") or {}).get("latest_price_date"),
                "latest_financial_disclosure_date": (jq.get("source_dates") or {}).get("latest_financial_disclosure_date"),
                "latest_dividend_pub_date": (jq.get("source_dates") or {}).get("latest_dividend_pub_date"),
                "source_snapshot": jq.get("source_snapshot") or {},
                "market": (jq.get("entity") or {}).get("market"),
                "sector33": (jq.get("entity") or {}).get("sector33"),
                "features": {
                    key: features.get(key) or {}
                    for key in _JQUANTS_CONTEXT_FEATURES
                },
                "evidence_ref": {
                    "derived_path": rel(jquants.get("features_path")) if jquants.get("features_path") else None,
                    "feature_set": jq.get("feature_set"),
                    "input_manifest_digest": (jq.get("input") or {}).get("input_manifest_digest"),
                },
                "claim": "CALCULATION",
            }
    return {
        "status": "UNKNOWN",
        "feature_set": JQUANTS_FEATURE_SET,
        "jquants_asof": jquants.get("asof"),
        "company_map_asof": (company_map or {}).get("asof"),
        "securities_code": None,
        "reason": "EDINET code と J-Quants securities_code の derived mapping が不足",
        "features": {},
        "evidence_ref": None,
        "claim": "UNKNOWN",
    }


_CROSS_CHECK_MAP = (
    ("revenue_growth_yoy", "sales_growth_yoy", 0.02),
    ("operating_margin", "operating_margin", 0.02),
    ("net_margin", "net_margin", 0.02),
    ("roe_proxy", "roe_proxy", 0.03),
    ("equity_ratio", "equity_ratio", 0.03),
)


def _calc_value(features: dict, key: str):
    m = features.get(key) or {}
    if not isinstance(m, dict) or m.get("status") != "CALCULATION":
        return None
    v = m.get("value")
    return v if isinstance(v, (int, float)) else None


def _period_year(label: dict | None):
    if not isinstance(label, dict):
        return None
    fiscal_year = label.get("fiscal_year")
    if isinstance(fiscal_year, int):
        return fiscal_year
    if isinstance(fiscal_year, float) and fiscal_year.is_integer():
        return int(fiscal_year)
    for key in ("period_end", "fiscal_year_end", "fiscalYearEnd"):
        value = label.get(key)
        if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
    return None


def _period_alignment(doc: dict, market_context: dict) -> dict:
    ed_current = (doc.get("source_snapshot") or {}).get("current_period")
    jq_current = ((market_context.get("source_snapshot") or {}).get("financial_current_period"))
    ed_year = _period_year(ed_current)
    jq_year = _period_year(jq_current)
    if ed_year is None or jq_year is None:
        return {
            "period_status": "UNKNOWN",
            "period_comparable": True,
            "edinet_period_year": ed_year,
            "jquants_period_year": jq_year,
        }
    comparable = ed_year == jq_year
    return {
        "period_status": "matched" if comparable else "period_mismatch",
        "period_comparable": comparable,
        "edinet_period_year": ed_year,
        "jquants_period_year": jq_year,
    }


def edinet_jquants_cross_check(doc: dict, market_context: dict | None) -> dict:
    """Compare overlapping derived ratios. This is an audit check, not a verdict."""
    market_context = market_context or {}
    if market_context.get("status") != "matched":
        return {
            "status": "UNKNOWN",
            "reason": "J-Quants market context が未結合",
            "checks": [],
            "mismatches": [],
        }
    edinet_features = doc.get("features") or {}
    jq_features = market_context.get("features") or {}
    period = _period_alignment(doc, market_context)
    checks = []
    mismatches = []
    period_mismatches = []
    for ed_key, jq_key, tolerance in _CROSS_CHECK_MAP:
        ed_val = _calc_value(edinet_features, ed_key)
        jq_val = _calc_value(jq_features, jq_key)
        if ed_val is None or jq_val is None:
            continue
        delta = jq_val - ed_val
        ok = None if not period["period_comparable"] else abs(delta) <= tolerance
        row = {
            "edinet_feature": ed_key,
            "jquants_feature": jq_key,
            "edinet_value": ed_val,
            "jquants_value": jq_val,
            "delta": delta,
            "tolerance": tolerance,
            "within_tolerance": ok,
            **period,
        }
        checks.append(row)
        if ok is None:
            period_mismatches.append(row)
            continue
        if not ok:
            mismatches.append(row)
    return {
        "status": "CALCULATION" if checks else "UNKNOWN",
        "reason": None if checks else "比較可能な重複指標が不足",
        "checks": checks,
        "mismatches": mismatches,
        "period_mismatches": period_mismatches,
        "period_status": period["period_status"],
    }


def jquants_summary(manifest: dict | None, *, manifest_path: Path | None = None) -> dict:
    if not isinstance(manifest, dict):
        return {"status": "UNKNOWN", "feature_set": JQUANTS_FEATURE_SET}
    return {
        "status": "CALCULATION",
        "feature_set": manifest.get("feature_set"),
        "asof": manifest.get("asof"),
        "generated_at": manifest.get("generated_at"),
        "coverage": manifest.get("coverage") or {},
        "distribution": {
            key: (manifest.get("distribution") or {}).get(key) or {}
            for key in ("return_20d", "return_60d", "return_252d", "operating_margin",
                        "roe_proxy", "per_trailing", "pbr")
        },
        "valuation_alias_hits": manifest.get("valuation_alias_hits") or {},
        "derived_path": rel(manifest_path) if manifest_path else None,
    }


def rel(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def metric_value(m: dict) -> str:
    if not isinstance(m, dict) or m.get("status") == "UNKNOWN":
        return "UNKNOWN"
    v = m.get("value")
    unit = m.get("unit")
    if unit == "bool" and isinstance(v, bool):
        return "true" if v else "false"
    if not isinstance(v, (int, float)):
        return "UNKNOWN"
    if unit == "ratio":
        return f"{v * 100:.1f}%"
    if unit == "JPY":
        return f"{v:,.0f} JPY"
    if unit:
        return f"{v} {unit}"
    return str(v)


def assert_no_forbidden_output(text: str) -> None:
    hits = [t for t in FORBIDDEN_OUTPUT_TOKENS if t in text]
    if hits:
        raise SystemExit(f"出力禁止語が混入しています: {hits}")
