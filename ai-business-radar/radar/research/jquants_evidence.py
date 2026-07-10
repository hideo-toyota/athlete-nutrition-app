"""Render local evidence packs from J-Quants derived features (point-in-time price).

Reads only `data/derived/features/jquants_equity_v1/<asof>/features.jsonl`.
No network, no raw-body reads, no recommendations/rankings/predictions.
The point of this module: surface the "当時の株価" (PIT adjusted close as of asof)
plus J-Quants fundamentals so the analysis brief can reason on price.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import DISCLAIMER, ROOT, assert_no_forbidden_output, latest_asof, metric_value, valid_asof

JQUANTS_FEATURE_SET = "jquants_equity_v1"
_SEC_RE = re.compile(r"^[0-9A-Z]{4,5}$")

VALUATION_ORDER = (
    "market_cap_jpy",
    "per_trailing",
    "pbr",
    "shares_outstanding",
    "eps_trailing",
    "bps",
)

FUNDAMENTAL_ORDER = (
    "sales_growth_yoy",
    "operating_margin",
    "net_margin",
    "roe_proxy",
    "equity_ratio",
    "dividend_record_present",
)


def valid_securities_code(code: str) -> str:
    if not isinstance(code, str):
        raise SystemExit("J-Quants evidence は証券コード(例 7203)で指定してください")
    code = code.strip().upper()
    if not _SEC_RE.match(code):
        raise SystemExit(f"J-Quants evidence は証券コード(例 7203)で指定してください: {code}")
    return code


def _feature_root(derived_root: Path | None) -> Path:
    base = derived_root or (ROOT / "data" / "derived")
    return base / "features" / JQUANTS_FEATURE_SET


def load_jquants_feature(code: str, *, asof: str | None = None, derived_root: Path | None = None) -> tuple[str, dict]:
    code = valid_securities_code(code)
    root = _feature_root(derived_root)
    asof = valid_asof(asof) or latest_asof(root)
    path = root / asof / "features.jsonl"
    if not path.exists():
        raise SystemExit(f"J-Quants derived features が見つかりません: {path}")
    # J-Quants uses 5-digit codes (4-digit ticker + trailing 0); accept either form.
    candidates = {code}
    if len(code) == 4:
        candidates.add(code + "0")
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"J-Quants features.jsonl が不正です({path}): {e}") from e
            sc = str(obj.get("securities_code", "")).strip().upper()
            if sc in candidates:
                return asof, obj
    raise SystemExit(f"securities_code {code} の J-Quants feature が {asof} に見つかりません")


def build_jquants_evidence(code: str, *, asof: str | None = None, derived_root: Path | None = None) -> dict:
    asof, doc = load_jquants_feature(code, asof=asof, derived_root=derived_root)
    return {"asof": asof, "doc": doc}


def render_jquants_evidence(evidence: dict) -> str:
    doc = evidence["doc"]
    asof = evidence["asof"]
    feats = doc.get("features") or {}
    ent = doc.get("entity") or {}
    sd = doc.get("source_dates") or {}
    code = doc.get("securities_code")
    name = ent.get("company_name") or ""
    title = f"# J-Quants Evidence — {code} {name}".rstrip()
    out = [
        title,
        "",
        f"_asof: {asof} / market: {ent.get('market')} / sector33: {ent.get('sector33')} / feature_set: {JQUANTS_FEATURE_SET}_",
        "",
        f"> {DISCLAIMER}",
        "",
        "## 当時の株価(PIT) [FACT/CALCULATION]",
        f"- latest_close: {metric_value(feats.get('latest_close') or {})}  ← asof以前の最終取引日の調整後終値(当時の株価)",
        f"- latest_price_date: `{sd.get('latest_price_date')}`",
        f"- latest_volume: {metric_value(feats.get('latest_volume') or {})}",
        f"- return_20d / 60d / 252d: {metric_value(feats.get('return_20d') or {})}"
        f" / {metric_value(feats.get('return_60d') or {})} / {metric_value(feats.get('return_252d') or {})}",
        "",
        "## バリュエーション(trailing) [CALCULATION/UNKNOWN]",
        "| feature | status | value |",
        "|---|---|---|",
    ]
    for key in VALUATION_ORDER:
        m = feats.get(key) or {}
        out.append(f"| {key} | {m.get('status', 'UNKNOWN')} | {metric_value(m)} |")
    out.extend([
        "",
        "## ファンダ(J-Quants summary由来) [CALCULATION/UNKNOWN]",
        "| feature | status | value |",
        "|---|---|---|",
    ])
    for key in FUNDAMENTAL_ORDER:
        m = feats.get(key) or {}
        out.append(f"| {key} | {m.get('status', 'UNKNOWN')} | {metric_value(m)} |")
    out.extend([
        "",
        "## 由来日付 [FACT]",
        f"- latest_price_date: `{sd.get('latest_price_date')}`",
        f"- latest_financial_disclosure_date: `{sd.get('latest_financial_disclosure_date')}`",
        f"- latest_dividend_pub_date: `{sd.get('latest_dividend_pub_date')}`",
        "",
        "## 注意",
        "- latest_close は調整後終値(adjusted close when available)。「当時の株価」= asof以前の最終取引日。",
        "- market_cap_jpy は latest_close×shares_outstanding のPIT proxy。時価総額順・売買順ではない。",
        "- per_trailing/pbr は trailing(直近本決算ベース)。予想PERではない。EPS/BPS が無い銘柄は UNKNOWN。",
        "- per/pbr の EPS/BPS は bulk の列エイリアス由来。coverage は summary の valuation_coverage_ratio で要確認。",
        "- roe_proxy は監査済ROEではない(proxy)。赤字/債務超過は per/pbr を UNKNOWN にしている。",
        "- 売買指示・順位・予測ではありません。最終判断は人間、discipline check 未通過。",
        "",
    ])
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_jquants_evidence(evidence: dict, *, outputs_root: Path | None = None) -> dict:
    code = valid_securities_code(evidence["doc"].get("securities_code"))
    root = outputs_root or (ROOT / "outputs")
    out_dir = root / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"jquants_{code}.md"
    p.write_text(render_jquants_evidence(evidence), encoding="utf-8")
    return {"path": p, "securities_code": code}
