"""Aggregate data-quality audits across research items.

This is a discipline/honesty instrument: it reports how well the data lines up,
NOT what to buy. No ranking, no recommendation, no prediction.

Three views (all meant to be run on real local derived data on the Mac):
  A. EDINET vs J-Quants cross-check aggregate (from the research queue): per
     overlapping metric — checked / mismatch counts, mismatch rate, and the
     |delta| distribution, so tolerance values can be judged on real data.
  B. J-Quants valuation coverage (from the jquants manifest): coverage ratio,
     which column aliases matched, and why stocks are still uncovered.
  C. J-Quants relative price consistency: grouped distributions only, used to
     inspect whether returns and valuation multiples are internally coherent.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from .common import DISCLAIMER, ROOT, assert_no_forbidden_output, finite_number, format_pct, load_jquants_context, rel
from .queue import build_research_queue

_MISSING_EDINET_MARKERS = (
    "derived feature directory が見つかりません",
    "derived feature asof directory がありません",
    "derived feature asof directory が見つかりません",
    "derived feature JSON がありません",
)


def aggregate_cross_checks(queue: dict, *, max_examples_per_metric: int = 5) -> dict:
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
                key, {"checked": 0, "mismatch": 0, "period_mismatch": 0, "abs_deltas": [], "tolerance": row.get("tolerance"),
                      "mismatch_examples": []})
            if row.get("within_tolerance") is None:
                agg["period_mismatch"] += 1
                continue
            agg["checked"] += 1
            agg["abs_deltas"].append(abs(row["delta"]))
            if not row.get("within_tolerance"):
                agg["mismatch"] += 1
                agg["mismatch_examples"].append({
                    "edinet_code": item.get("edinet_code"),
                    "securities_code": item.get("ticker"),
                    "edinet_period_year": row.get("edinet_period_year"),
                    "jquants_period_year": row.get("jquants_period_year"),
                    "period_status": row.get("period_status"),
                    "edinet_value": row.get("edinet_value"),
                    "jquants_value": row.get("jquants_value"),
                    "delta": row.get("delta"),
                    "abs_delta": abs(row["delta"]),
                    "diagnosis": _diagnose_mismatch(key, row),
                })
    metrics = {}
    for key, agg in sorted(per_metric.items()):
        deltas = agg["abs_deltas"]
        examples = sorted(agg["mismatch_examples"], key=lambda x: x["abs_delta"], reverse=True)
        tolerance = agg["tolerance"]
        median = statistics.median(deltas) if deltas else None
        p75 = _percentile(deltas, 0.75)
        p90 = _percentile(deltas, 0.90)
        max_delta = max(deltas) if deltas else None
        mismatch_rate = (agg["mismatch"] / agg["checked"]) if agg["checked"] else None
        metrics[key] = {
            "checked": agg["checked"],
            "mismatch": agg["mismatch"],
            "period_mismatch": agg["period_mismatch"],
            "mismatch_rate": mismatch_rate,
            "tolerance": tolerance,
            "median_abs_delta": median,
            "p75_abs_delta": p75,
            "p90_abs_delta": p90,
            "max_abs_delta": max_delta,
            "calibration_signal": _calibration_signal(
                checked=agg["checked"],
                mismatch_rate=mismatch_rate,
                tolerance=tolerance,
                median_abs_delta=median,
                p90_abs_delta=p90,
                max_abs_delta=max_delta,
            ),
            "mismatch_examples": examples[:max_examples_per_metric],
        }
    return {"item_count": len(items), "cross_checked_items": cross_checked_items, "metrics": metrics}


def _diagnose_mismatch(metric_key: str, row: dict) -> str:
    """Human-facing triage hint for top mismatches.

    This is not a FACT conclusion. It tells the operator what to inspect next so
    we do not "fix" tolerances before checking period/definition/data issues.
    """
    ed = row.get("edinet_value")
    jq = row.get("jquants_value")
    delta = row.get("delta")
    if row.get("period_comparable") is False:
        return "period_mismatch: 対象FY差を先に解消"
    if metric_key.startswith("revenue_growth_yoy"):
        if isinstance(jq, (int, float)) and abs(jq) < 0.0000001 and isinstance(ed, (int, float)) and abs(ed) >= 0.02:
            return "J-Quants成長率0.0: 欠損補完/前年比分母/売上定義を点検"
        return "売上定義・決算期間・前年比分母の差を点検"
    if metric_key.startswith("operating_margin"):
        return "営業利益定義・連結/単体・販管費/一過性項目を点検"
    if metric_key.startswith("net_margin"):
        return "当期利益定義・親会社帰属/非支配持分・一過性損益を点検"
    if metric_key.startswith("roe_proxy"):
        return "平均自己資本 vs 期末自己資本・利益定義を点検"
    if metric_key.startswith("equity_ratio"):
        if isinstance(delta, (int, float)) and abs(delta) >= 0.10:
            return "自己資本/純資産定義・非支配株主持分・連結範囲を重点点検"
        return "自己資本/純資産定義・連結範囲を点検"
    return "定義差・入力列・期間差を点検"


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def _calibration_signal(*, checked: int, mismatch_rate, tolerance, median_abs_delta,
                        p90_abs_delta, max_abs_delta) -> str:
    """Human-review signal only. It must not auto-change tolerance."""
    if checked < 20:
        return "sample_too_small"
    if not isinstance(mismatch_rate, (int, float)):
        return "unknown"
    if not isinstance(tolerance, (int, float)) or tolerance <= 0:
        return "tolerance_missing_or_zero"
    median = median_abs_delta if isinstance(median_abs_delta, (int, float)) else 0.0
    p90 = p90_abs_delta if isinstance(p90_abs_delta, (int, float)) else 0.0
    mx = max_abs_delta if isinstance(max_abs_delta, (int, float)) else 0.0
    if mismatch_rate >= 0.40:
        return "definition_or_period_review"
    if median > tolerance:
        return "systematic_shift_or_tolerance_review"
    if p90 > tolerance * 3 or mx > tolerance * 10:
        return "outlier_review"
    if mismatch_rate >= 0.20:
        return "monitor_definition_drift"
    return "ok"


def valuation_coverage_view(jquants: dict) -> dict:
    manifest = jquants.get("manifest") or {}
    coverage = manifest.get("coverage") or {}
    listed = coverage.get("listed_codes")
    covered = coverage.get("valuation_covered")
    has_uncovered_reasons = "valuation_uncovered_reasons" in coverage
    stale_uncovered_reasons = (
        isinstance(listed, int)
        and isinstance(covered, int)
        and covered < listed
        and not has_uncovered_reasons
    )
    return {
        "asof": jquants.get("asof"),
        "feature_set": manifest.get("feature_set"),
        "listed_codes": listed,
        "valuation_covered": covered,
        "valuation_coverage_ratio": coverage.get("valuation_coverage_ratio"),
        "market_cap_covered": coverage.get("market_cap_covered"),
        "market_cap_coverage_ratio": coverage.get("market_cap_coverage_ratio"),
        "price_coverage_ratio": coverage.get("price_coverage_ratio"),
        "per_covered": coverage.get("per_covered"),
        "per_coverage_ratio": coverage.get("per_coverage_ratio"),
        "per_uncovered_reasons": coverage.get("per_uncovered_reasons") or {},
        "pbr_covered": coverage.get("pbr_covered"),
        "pbr_coverage_ratio": coverage.get("pbr_coverage_ratio"),
        "pbr_uncovered_reasons": coverage.get("pbr_uncovered_reasons") or {},
        "valuation_alias_hits": manifest.get("valuation_alias_hits") or {},
        "valuation_uncovered_reasons": coverage.get("valuation_uncovered_reasons") or {},
        "needs_rebuild_for_uncovered_reasons": stale_uncovered_reasons,
        "manifest_path": rel(jquants.get("manifest_path")) if jquants.get("manifest_path") else None,
    }


def _calc_feature(doc: dict, key: str) -> float | None:
    feature = (doc.get("features") or {}).get(key) or {}
    if not isinstance(feature, dict) or feature.get("status") != "CALCULATION":
        return None
    return finite_number(feature.get("value"))


def _jquants_rows(jquants: dict) -> list[dict]:
    docs_by_code: dict[str, dict] = {}
    for doc in (jquants.get("by_code") or {}).values():
        code = doc.get("securities_code")
        if isinstance(code, str):
            docs_by_code[code] = doc
    rows = []
    for code in sorted(docs_by_code):
        doc = docs_by_code[code]
        entity = doc.get("entity") or {}
        market = entity.get("market") or "UNKNOWN"
        sector = entity.get("sector33") or "UNKNOWN"
        if market == "その他" or sector == "その他":
            continue
        rows.append({
            "securities_code": code,
            "market": market,
            "sector33": sector,
            "per_trailing": _calc_feature(doc, "per_trailing"),
            "pbr": _calc_feature(doc, "pbr"),
            "return_20d": _calc_feature(doc, "return_20d"),
            "return_60d": _calc_feature(doc, "return_60d"),
            "market_cap_jpy": _calc_feature(doc, "market_cap_jpy"),
        })
    return rows


def _clean(values) -> list[float]:
    return [v for v in (finite_number(x) for x in values) if v is not None]


def _distribution(values) -> dict:
    clean = _clean(values)
    return {
        "count": len(clean),
        "median": statistics.median(clean) if clean else None,
        "p10": _percentile(clean, 0.10),
        "p90": _percentile(clean, 0.90),
    }


def _outside_band(value, dist: dict) -> bool:
    v = finite_number(value)
    p10 = finite_number(dist.get("p10"))
    p90 = finite_number(dist.get("p90"))
    if v is None or p10 is None or p90 is None:
        return False
    return v < p10 or v > p90


def _group_relative_stats(group_type: str, group_name: str, rows: list[dict]) -> dict:
    per = _distribution(r.get("per_trailing") for r in rows)
    pbr = _distribution(r.get("pbr") for r in rows)
    r20 = _distribution(r.get("return_20d") for r in rows)
    r60 = _distribution(r.get("return_60d") for r in rows)
    market_cap = _distribution(r.get("market_cap_jpy") for r in rows)
    n = len(rows)
    joint_deviation_count = 0
    if n >= 5:
        for row in rows:
            return_deviation = _outside_band(row.get("return_20d"), r20)
            valuation_deviation = (
                _outside_band(row.get("per_trailing"), per)
                or _outside_band(row.get("pbr"), pbr)
            )
            if return_deviation and valuation_deviation:
                joint_deviation_count += 1
    return {
        "group_type": group_type,
        "group": group_name,
        "status": "CALCULATION" if n >= 3 else "UNKNOWN",
        "sample_count": n,
        "per_coverage_ratio": per["count"] / n if n else None,
        "pbr_coverage_ratio": pbr["count"] / n if n else None,
        "return_20d_coverage_ratio": r20["count"] / n if n else None,
        "per_median": per["median"],
        "pbr_median": pbr["median"],
        "return_20d_median": r20["median"],
        "return_20d_p10": r20["p10"],
        "return_20d_p90": r20["p90"],
        "return_60d_median": r60["median"],
        "market_cap_median": market_cap["median"],
        "joint_deviation_count": joint_deviation_count if n >= 5 else None,
        "note": "sample_too_small" if n < 3 else "group_distribution_only",
    }


def relative_price_consistency_view(jquants: dict) -> dict:
    """Group-level relative price audit, not a securities list.

    The Jane-Street-style lesson we can safely reuse is internal consistency:
    compare related prices and multiples. For a personal-investor tool this must
    stay at grouped distribution level, because individual outlier lists can
    easily become trade suggestions.
    """
    rows = _jquants_rows(jquants)
    if not rows:
        return {
            "status": "UNKNOWN",
            "asof": jquants.get("asof"),
            "reason": "J-Quants derived rows が不足",
            "common_equity_rows": 0,
            "groups": [],
        }
    groups: list[dict] = []
    groups.append(_group_relative_stats("all_common_equity", "ALL", rows))
    for group_type, key in (("market", "market"), ("sector33", "sector33")):
        names = sorted({r.get(key) or "UNKNOWN" for r in rows})
        for name in names:
            subset = [r for r in rows if (r.get(key) or "UNKNOWN") == name]
            groups.append(_group_relative_stats(group_type, name, subset))
    calculable = [g for g in groups if g["status"] == "CALCULATION"]
    return {
        "status": "CALCULATION" if calculable else "UNKNOWN",
        "asof": jquants.get("asof"),
        "common_equity_rows": len(rows),
        "groups": groups,
        "calculation_group_count": len(calculable),
        "scope": "group_distribution_only",
    }


def build_audit_report(*, asof: str | None = None, derived_root: Path | None = None) -> dict:
    try:
        queue = build_research_queue(asof=asof, derived_root=derived_root)
        cross = aggregate_cross_checks(queue)
        eff_asof = queue["asof"]
    except SystemExit as e:
        message = str(e)
        if not any(marker in message for marker in _MISSING_EDINET_MARKERS):
            raise
        cross = {"item_count": 0, "cross_checked_items": 0, "metrics": {},
                 "reason": f"EDINET derived features 不足のため cross-check は未集計: {message}"}
        eff_asof = None
    jquants = load_jquants_context(asof=asof, derived_root=derived_root)
    return {
        "asof": eff_asof or jquants.get("asof"),
        "cross_check": cross,
        "valuation": valuation_coverage_view(jquants),
        "relative_price_consistency": relative_price_consistency_view(jquants),
    }


def _pct(value) -> str:
    return format_pct(value)


def _pt(value) -> str:
    v = finite_number(value)
    return "UNKNOWN" if v is None else f"{v * 100:.2f}pt"


def _multiple(value) -> str:
    v = finite_number(value)
    return "UNKNOWN" if v is None else f"{v:.2f}x"


def _int_or_unknown(value) -> str:
    v = finite_number(value)
    return "UNKNOWN" if v is None else str(int(v))


def render_audit_report(report: dict) -> str:
    cc = report.get("cross_check") or {}
    val = report.get("valuation") or {}
    rpc = report.get("relative_price_consistency") or {}
    out = [
        "# Data Quality Audit — EDINET×J-Quants 整合 / valuation coverage / relative price consistency",
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
            "| metric | checked | mismatch | period_mismatch | mismatch率 | tolerance | median|Δ| | p90|Δ| | max|Δ| | 校正信号 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for key, m in metrics.items():
            out.append(
                f"| {key} | {m['checked']} | {m['mismatch']} | {m.get('period_mismatch', 0)} | {_pct(m['mismatch_rate'])} | "
                f"{_pt(m['tolerance'])} | {_pt(m['median_abs_delta'])} | {_pt(m.get('p90_abs_delta'))} | "
                f"{_pt(m['max_abs_delta'])} | `{m.get('calibration_signal', 'unknown')}` |"
            )
        out.extend([
            "",
            "- mismatch率が高い指標は、tolerance が厳しすぎるか、片側のデータ品質/定義差を示す(要点検)。",
            "- median|Δ| が tolerance に近い指標は、tolerance 見直しの候補。",
            "- p90|Δ| が tolerance を大きく超え、median|Δ| が小さい場合は、全体調整より外れ値/期間差/定義差を優先点検。",
            "- period_mismatch は EDINET と J-Quants の対象FYが違うため、mismatch率の分母から除外。",
            "- 校正信号は自動判定ではなく、次に見るべきデータ品質タスクのラベル。",
        ])
        examples = [
            (key, example)
            for key, m in metrics.items()
            for example in (m.get("mismatch_examples") or [])
        ]
        if examples:
            out.extend([
                "",
                "### mismatch 原因分解(絶対差が大きい順・各指標最大5件)",
                "| metric | edinet_code | sec_code | EDINET FY | JQ FY | EDINET | J-Quants | delta | 推定原因/次点検 |",
                "|---|---|---|---:|---:|---:|---:|---:|---|",
            ])
            for key, ex in examples:
                out.append(
                    f"| {key} | {ex.get('edinet_code')} | {ex.get('securities_code')} | "
                    f"{ex.get('edinet_period_year') or 'UNKNOWN'} | {ex.get('jquants_period_year') or 'UNKNOWN'} | "
                    f"{_pct(ex.get('edinet_value'))} | {_pct(ex.get('jquants_value'))} | {_pt(ex.get('delta'))} | "
                    f"{ex.get('diagnosis') or 'UNKNOWN'} |"
                )
    out.extend([
        "",
        "## B. J-Quants valuation coverage [CALCULATION/UNKNOWN]",
        f"- feature_set/asof: `{val.get('feature_set')}` / `{val.get('asof')}`",
        f"- listed_codes: {val.get('listed_codes')} / valuation_covered: {val.get('valuation_covered')}",
        f"- valuation_coverage: {_pct(val.get('valuation_coverage_ratio'))} / "
        f"price_coverage: {_pct(val.get('price_coverage_ratio'))}",
        f"- market_cap_coverage: {_pct(val.get('market_cap_coverage_ratio'))} / "
        f"market_cap_covered: {val.get('market_cap_covered')}",
        f"- per_coverage: {_pct(val.get('per_coverage_ratio'))} / pbr_coverage: {_pct(val.get('pbr_coverage_ratio'))}",
        f"- alias_hits: `{json.dumps(val.get('valuation_alias_hits') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- uncovered_reasons: `{json.dumps(val.get('valuation_uncovered_reasons') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- per_uncovered_reasons: `{json.dumps(val.get('per_uncovered_reasons') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- pbr_uncovered_reasons: `{json.dumps(val.get('pbr_uncovered_reasons') or {}, ensure_ascii=False, sort_keys=True)}`",
        "",
    ])
    if val.get("needs_rebuild_for_uncovered_reasons"):
        out.extend([
            "- ⚠️ uncovered_reasons が未生成です。先に `python3 -m radar build-jquants-features --asof <日付>` を再実行してください。",
            "",
        ])
    out.extend([
        "- uncovered の `no_per_pbr_inputs` が多い場合、EPS/BPS 列エイリアスが実 raw と不一致の可能性(要列名確認)。",
        "- PER/PBR 個別の未カバーは `per_uncovered_reasons` / `pbr_uncovered_reasons` を優先して確認。",
        "- `nonpositive_or_unusable_inputs` は赤字/債務超過など。算出不能で正しく UNKNOWN。",
        "- `no_price` は価格欠損。価格 bulk の範囲/銘柄を確認。",
        "",
        "## C. J-Quants relative price consistency [CALCULATION/UNKNOWN]",
        "- 方向予測ではなく、同じ市場・業種内で価格リターンとPER/PBRの分布が同時に大きく外れていないかを見る監査です。",
        "- 個別銘柄リストは出しません。市場区分・業種単位の分布だけを出し、調査順序や売買判断には使いません。",
        f"- status/asof: `{rpc.get('status', 'UNKNOWN')}` / `{rpc.get('asof') or 'UNKNOWN'}`",
        f"- common_equity_rows: {rpc.get('common_equity_rows', 0)} / calculation_groups: {rpc.get('calculation_group_count', 0)}",
        "",
    ])
    groups = rpc.get("groups") or []
    if groups:
        out.extend([
            "| group_type | group | status | n | PER cov | PBR cov | 20d cov | PER med | PBR med | 20d med | 20d p10/p90 | joint_deviation_count | note |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for g in groups:
            out.append(
                f"| {g.get('group_type')} | {g.get('group')} | {g.get('status')} | {g.get('sample_count')} | "
                f"{_pct(g.get('per_coverage_ratio'))} | {_pct(g.get('pbr_coverage_ratio'))} | "
                f"{_pct(g.get('return_20d_coverage_ratio'))} | "
                f"{_multiple(g.get('per_median'))} | {_multiple(g.get('pbr_median'))} | "
                f"{_pct(g.get('return_20d_median'))} | {_pct(g.get('return_20d_p10'))}/{_pct(g.get('return_20d_p90'))} | "
                f"{_int_or_unknown(g.get('joint_deviation_count'))} | `{g.get('note') or 'UNKNOWN'}` |"
            )
    else:
        out.append("- status: UNKNOWN — J-Quants derived rows が不足")
    out.extend([
        "",
        "- joint_deviation_count は、同一グループ内で20日リターンとPER/PBRの双方が10-90%帯の外に出た件数。",
        "- 件数が多いグループは、ニュース・決算期ズレ・倍率計算の入力列・流動性を点検します。魅力度ではありません。",
        "",
        "## 注意",
        "- per/pbr は trailing(予想PERではない)。本レポートは魅力度・売買順ではありません。",
        "- market_cap_jpy は latest_close×shares_outstanding のPIT proxy。投資判断の優先度ではありません。",
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
