"""Aggregate data-quality audits across research items.

This is a discipline/honesty instrument: it reports how well the data lines up,
NOT what to buy. No ranking, no recommendation, no prediction.

Two views (both meant to be run on real local derived data on the Mac):
  A. EDINET vs J-Quants cross-check aggregate (from the research queue): per
     overlapping metric — checked / mismatch counts, mismatch rate, and the
     |delta| distribution, so tolerance values can be judged on real data.
  B. J-Quants valuation coverage (from the jquants manifest): coverage ratio,
     which column aliases matched, and why stocks are still uncovered.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from .common import DISCLAIMER, ROOT, assert_no_forbidden_output, load_jquants_context, rel
from .queue import build_research_queue


def aggregate_cross_checks(queue: dict) -> dict:
    per_metric: dict[str, dict] = {}
    items = queue.get("items") or []
    cross_checked_items = 0
    for item in items:
        cc = item.get("edinet_jquants_cross_check") or {}
        if cc.get("status") != "CALCULATION":
            continue
        cross_checked_items += 1
        for row in cc.get("checks") or []:
            key = f"{row['edinet_feature']}↔{row['jquants_feature']}"
            agg = per_metric.setdefault(
                key, {"checked": 0, "mismatch": 0, "abs_deltas": [], "tolerance": row.get("tolerance")})
            agg["checked"] += 1
            agg["abs_deltas"].append(abs(row["delta"]))
            if not row.get("within_tolerance"):
                agg["mismatch"] += 1
    metrics = {}
    for key, agg in sorted(per_metric.items()):
        deltas = agg["abs_deltas"]
        metrics[key] = {
            "checked": agg["checked"],
            "mismatch": agg["mismatch"],
            "mismatch_rate": (agg["mismatch"] / agg["checked"]) if agg["checked"] else None,
            "tolerance": agg["tolerance"],
            "median_abs_delta": statistics.median(deltas) if deltas else None,
            "max_abs_delta": max(deltas) if deltas else None,
        }
    return {"item_count": len(items), "cross_checked_items": cross_checked_items, "metrics": metrics}


def valuation_coverage_view(jquants: dict) -> dict:
    manifest = jquants.get("manifest") or {}
    coverage = manifest.get("coverage") or {}
    return {
        "asof": jquants.get("asof"),
        "feature_set": manifest.get("feature_set"),
        "listed_codes": coverage.get("listed_codes"),
        "valuation_covered": coverage.get("valuation_covered"),
        "valuation_coverage_ratio": coverage.get("valuation_coverage_ratio"),
        "price_coverage_ratio": coverage.get("price_coverage_ratio"),
        "valuation_alias_hits": manifest.get("valuation_alias_hits") or {},
        "valuation_uncovered_reasons": coverage.get("valuation_uncovered_reasons") or {},
        "manifest_path": rel(jquants.get("manifest_path")) if jquants.get("manifest_path") else None,
    }


def build_audit_report(*, asof: str | None = None, derived_root: Path | None = None) -> dict:
    try:
        queue = build_research_queue(asof=asof, derived_root=derived_root)
        cross = aggregate_cross_checks(queue)
        eff_asof = queue["asof"]
    except SystemExit:
        cross = {"item_count": 0, "cross_checked_items": 0, "metrics": {},
                 "reason": "EDINET derived features 不足のため cross-check は未集計"}
        eff_asof = None
    jquants = load_jquants_context(asof=asof, derived_root=derived_root)
    return {
        "asof": eff_asof or jquants.get("asof"),
        "cross_check": cross,
        "valuation": valuation_coverage_view(jquants),
    }


def _pct(value) -> str:
    return "UNKNOWN" if not isinstance(value, (int, float)) else f"{value * 100:.1f}%"


def _pt(value) -> str:
    return "UNKNOWN" if not isinstance(value, (int, float)) else f"{value * 100:.2f}pt"


def render_audit_report(report: dict) -> str:
    cc = report.get("cross_check") or {}
    val = report.get("valuation") or {}
    out = [
        "# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage",
        "",
        f"_asof: {report.get('asof')} / これは整合性の点検であり、売買順・推奨・予測ではありません_",
        "",
        f"> {DISCLAIMER}",
        "",
        "## A. EDINET vs J-Quants cross-check 集計 [CALCULATION/UNKNOWN]",
        f"- research items: {cc.get('item_count', 0)} / cross-checked: {cc.get('cross_checked_items', 0)}",
    ]
    if cc.get("reason"):
        out.append(f"- status: UNKNOWN — {cc['reason']}")
    metrics = cc.get("metrics") or {}
    if metrics:
        out.extend([
            "",
            "| metric | checked | mismatch | mismatch率 | tolerance | median|Δ| | max|Δ| |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ])
        for key, m in metrics.items():
            out.append(
                f"| {key} | {m['checked']} | {m['mismatch']} | {_pct(m['mismatch_rate'])} | "
                f"{_pt(m['tolerance'])} | {_pt(m['median_abs_delta'])} | {_pt(m['max_abs_delta'])} |"
            )
        out.extend([
            "",
            "- mismatch率が高い指標は、tolerance が厳しすぎるか、片側のデータ品質/定義差を示す(要点検)。",
            "- median|Δ| が tolerance に近い指標は、tolerance 見直しの候補。",
        ])
    out.extend([
        "",
        "## B. J-Quants valuation coverage [CALCULATION/UNKNOWN]",
        f"- feature_set/asof: `{val.get('feature_set')}` / `{val.get('asof')}`",
        f"- listed_codes: {val.get('listed_codes')} / valuation_covered: {val.get('valuation_covered')}",
        f"- valuation_coverage: {_pct(val.get('valuation_coverage_ratio'))} / "
        f"price_coverage: {_pct(val.get('price_coverage_ratio'))}",
        f"- alias_hits: `{json.dumps(val.get('valuation_alias_hits') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- uncovered_reasons: `{json.dumps(val.get('valuation_uncovered_reasons') or {}, ensure_ascii=False, sort_keys=True)}`",
        "",
        "- uncovered の `no_per_pbr_inputs` が多い場合、EPS/BPS 列エイリアスが実 raw と不一致の可能性(要列名確認)。",
        "- `nonpositive_or_unusable_inputs` は赤字/債務超過など。算出不能で正しく UNKNOWN。",
        "- `no_price` は価格欠損。価格 bulk の範囲/銘柄を確認。",
        "",
        "## 注意",
        "- per/pbr は trailing(予想PERではない)。本レポートは魅力度・売買順ではありません。",
        "- 第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用)。",
        "",
    ]
    )
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_audit_report(report: dict, *, outputs_root: Path | None = None) -> dict:
    root = outputs_root or (ROOT / "outputs")
    root.mkdir(parents=True, exist_ok=True)
    md = root / "data_quality_audit.md"
    manifest = root / "data_quality_audit.json"
    md.write_text(render_audit_report(report), encoding="utf-8")
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"md_path": md, "manifest_path": manifest}
