"""Daily investor brief from local derived features.

This module is a deterministic analysis layer for daily operation. It reads
derived features only, does not call network/LLM APIs, and does not emit trade
instructions or attractiveness ordering.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import (
    DISCLAIMER,
    JQUANTS_FEATURE_SET,
    ROOT,
    assert_no_forbidden_output,
    edinet_jquants_cross_check,
    jquants_market_context,
    jquants_summary,
    load_edinet_company_map,
    load_feature_docs,
    load_jquants_context,
    metric_value,
    rel,
    valid_asof,
)


def _feature(doc: dict, key: str) -> dict:
    return (doc.get("features") or {}).get(key) or {}


def _num(doc: dict, key: str) -> float | None:
    m = _feature(doc, key)
    if not isinstance(m, dict) or m.get("status") != "CALCULATION":
        return None
    v = m.get("value")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _text_feature(doc: dict, key: str) -> str:
    return metric_value(_feature(doc, key))


def _pct(value) -> str:
    return "UNKNOWN" if not isinstance(value, (int, float)) else f"{value * 100:.1f}%"


def _small_jpy(value) -> str:
    if not isinstance(value, (int, float)):
        return "UNKNOWN"
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.1f}兆円"
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f}億円"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.1f}万円"
    return f"{value:,.0f}円"


def _feature_root(feature_set: str, derived_root: Path | None = None) -> Path:
    return (derived_root or (ROOT / "data" / "derived")) / "features" / feature_set


def _latest_before(root: Path, asof: str) -> str | None:
    if not root.exists():
        return None
    dirs = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name < asof)
    return dirs[-1] if dirs else None


def _load_jquants_docs(*, asof: str, derived_root: Path | None = None) -> tuple[dict, list[dict]]:
    ctx = load_jquants_context(asof=asof, derived_root=derived_root)
    docs_by_code: dict[str, dict] = {}
    for doc in (ctx.get("by_code") or {}).values():
        code = doc.get("securities_code")
        if isinstance(code, str):
            docs_by_code[code] = doc
    return ctx, [docs_by_code[k] for k in sorted(docs_by_code)]


def _market_snapshot(jq_summary: dict) -> dict:
    coverage = jq_summary.get("coverage") or {}
    dist = jq_summary.get("distribution") or {}
    return {
        "status": jq_summary.get("status", "UNKNOWN"),
        "feature_set": jq_summary.get("feature_set"),
        "asof": jq_summary.get("asof"),
        "latest_price_date": coverage.get("latest_price_date"),
        "listed_codes": coverage.get("listed_codes"),
        "price_coverage_ratio": coverage.get("price_coverage_ratio"),
        "valuation_coverage_ratio": coverage.get("valuation_coverage_ratio"),
        "market_cap_coverage_ratio": coverage.get("market_cap_coverage_ratio"),
        "per_trailing_median": (dist.get("per_trailing") or {}).get("median"),
        "pbr_median": (dist.get("pbr") or {}).get("median"),
        "market_cap_median": (dist.get("market_cap_jpy") or {}).get("median"),
        "return_20d_median": (dist.get("return_20d") or {}).get("median"),
        "return_20d_positive_rate": (dist.get("return_20d") or {}).get("positive_rate"),
        "return_60d_median": (dist.get("return_60d") or {}).get("median"),
        "return_60d_positive_rate": (dist.get("return_60d") or {}).get("positive_rate"),
        "return_252d_median": (dist.get("return_252d") or {}).get("median"),
        "return_252d_positive_rate": (dist.get("return_252d") or {}).get("positive_rate"),
    }


def _brief_row(doc: dict, previous: dict | None = None) -> dict:
    entity = doc.get("entity") or {}
    row = {
        "securities_code": doc.get("securities_code") or "UNKNOWN",
        # Do not render provider text fields in the daily brief. The brief is
        # code-centric; names can be checked in local evidence if needed.
        "company_name": "名称非表示",
        "market": entity.get("market") or "UNKNOWN",
        "sector33": entity.get("sector33") or "UNKNOWN",
        "latest_price_date": (doc.get("source_dates") or {}).get("latest_price_date"),
        "latest_close": _num(doc, "latest_close"),
        "market_cap_jpy": _num(doc, "market_cap_jpy"),
        "per_trailing": _num(doc, "per_trailing"),
        "pbr": _num(doc, "pbr"),
        "return_20d": _num(doc, "return_20d"),
        "return_60d": _num(doc, "return_60d"),
        "return_252d": _num(doc, "return_252d"),
        "sales_growth_yoy": _num(doc, "sales_growth_yoy"),
        "operating_margin": _num(doc, "operating_margin"),
        "roe_proxy": _num(doc, "roe_proxy"),
        "equity_ratio": _num(doc, "equity_ratio"),
    }
    if previous is not None:
        prev_close = _num(previous, "latest_close")
        prev_per = _num(previous, "per_trailing")
        prev_pbr = _num(previous, "pbr")
        row["close_change_vs_previous_derived"] = (
            None if prev_close in (None, 0) or row["latest_close"] is None
            else row["latest_close"] / prev_close - 1
        )
        row["per_change_vs_previous_derived"] = (
            None if prev_per in (None, 0) or row["per_trailing"] is None
            else row["per_trailing"] / prev_per - 1
        )
        row["pbr_change_vs_previous_derived"] = (
            None if prev_pbr in (None, 0) or row["pbr"] is None
            else row["pbr"] / prev_pbr - 1
        )
    return row


def _is_common_equity_row(row: dict) -> bool:
    """Best-effort exclusion of ETFs/funds from the daily operating view."""
    return row.get("market") != "その他" and row.get("sector33") != "その他"


def _is_common_equity_item(item: dict) -> bool:
    mc = item.get("jquants_market_context") or {}
    return mc.get("market") != "その他" and mc.get("sector33") != "その他"


def _bounded(rows: list[dict], *, key, reverse=False, limit=8) -> list[dict]:
    valid = [r for r in rows if key(r) is not None]
    return sorted(valid, key=key, reverse=reverse)[:limit]


def _watch_changes(jq_docs: list[dict], previous_docs: dict[str, dict]) -> dict:
    rows = [
        r for r in (_brief_row(d, previous_docs.get(d.get("securities_code") or "")) for d in jq_docs)
        if _is_common_equity_row(r)
    ]
    large_declines_20d = _bounded(
        [r for r in rows if isinstance(r.get("return_20d"), float) and r["return_20d"] <= -0.10],
        key=lambda r: r.get("return_20d"),
        limit=8,
    )
    large_advances_20d = _bounded(
        [r for r in rows if isinstance(r.get("return_20d"), float) and r["return_20d"] >= 0.10],
        key=lambda r: r.get("return_20d"),
        reverse=True,
        limit=8,
    )
    small_cap_value_shape = sorted([
        r for r in rows
        if isinstance(r.get("market_cap_jpy"), float)
        and r["market_cap_jpy"] <= 10_000_000_000
        and isinstance(r.get("pbr"), float)
        and r["pbr"] <= 1.0
        and isinstance(r.get("per_trailing"), float)
        and 0 < r["per_trailing"] <= 20
    ], key=lambda r: (r["market_cap_jpy"], r["securities_code"]))[:10]
    derived_day_changes = _bounded(
        [r for r in rows if isinstance(r.get("close_change_vs_previous_derived"), float)
         and abs(r["close_change_vs_previous_derived"]) >= 0.03],
        key=lambda r: abs(r.get("close_change_vs_previous_derived") or 0),
        reverse=True,
        limit=8,
    )
    return {
        "large_declines_20d": large_declines_20d,
        "large_advances_20d": large_advances_20d,
        "small_cap_value_shape": small_cap_value_shape,
        "derived_day_changes": derived_day_changes,
        "previous_derived_available": bool(previous_docs),
    }


def _unknowns_for_item(item: dict) -> list[str]:
    mc = item.get("jquants_market_context") or {}
    mf = mc.get("features") or {}
    unknowns = []
    for key in ("per_trailing", "pbr", "market_cap_jpy", "return_20d", "return_60d"):
        if (mf.get(key) or {}).get("status") != "CALCULATION":
            unknowns.append(f"J-Quants {key}=UNKNOWN")
    for key in ("valuation_status", "roic_proxy"):
        if key in item.get("unknown_features", []):
            unknowns.append(f"EDINET {key}=UNKNOWN")
    return unknowns or ["主要価格/財務派生値は取得済み"]


def _fact_points_for_item(item: dict) -> list[str]:
    mc = item.get("jquants_market_context") or {}
    mf = mc.get("features") or {}
    points = [
        f"sec_code={mc.get('securities_code') or 'UNKNOWN'}",
        f"price_date={mc.get('latest_price_date') or 'UNKNOWN'}",
        f"close={metric_value(mf.get('latest_close') or {})}",
        f"market_cap={metric_value(mf.get('market_cap_jpy') or {})}",
        f"PER={metric_value(mf.get('per_trailing') or {})}",
        f"PBR={metric_value(mf.get('pbr') or {})}",
        f"20d={metric_value(mf.get('return_20d') or {})}",
        f"60d={metric_value(mf.get('return_60d') or {})}",
    ]
    return points


def _review_reason(item: dict) -> str | None:
    mc = item.get("jquants_market_context") or {}
    mf = mc.get("features") or {}
    market_cap = (mf.get("market_cap_jpy") or {}).get("value")
    pbr = (mf.get("pbr") or {}).get("value")
    per = (mf.get("per_trailing") or {}).get("value")
    r20 = (mf.get("return_20d") or {}).get("value")
    r60 = (mf.get("return_60d") or {}).get("value")
    mismatches = len((item.get("edinet_jquants_cross_check") or {}).get("mismatches") or [])
    period_mismatches = len((item.get("edinet_jquants_cross_check") or {}).get("period_mismatches") or [])
    if isinstance(r20, (int, float)) and abs(r20) >= 0.10:
        return "price_move_review"
    if isinstance(r60, (int, float)) and abs(r60) >= 0.20:
        return "medium_term_move_review"
    if (
        isinstance(market_cap, (int, float)) and market_cap <= 10_000_000_000
        and isinstance(pbr, (int, float)) and pbr <= 1.0
        and isinstance(per, (int, float)) and 0 < per <= 20
    ):
        return "small_cap_low_multiple_review"
    if mismatches:
        return "data_conflict_review"
    if period_mismatches >= 5:
        return "period_alignment_review"
    return None


def _human_review_list(queue_items: list[dict], *, limit: int) -> list[dict]:
    reason_order = {
        "price_move_review": 0,
        "medium_term_move_review": 1,
        "small_cap_low_multiple_review": 2,
        "data_conflict_review": 3,
        "period_alignment_review": 4,
    }
    def sort_value(item: dict, reason: str) -> float:
        mc = item.get("jquants_market_context") or {}
        mf = mc.get("features") or {}
        if reason == "price_move_review":
            r = (mf.get("return_20d") or {}).get("value")
            return abs(r) if isinstance(r, (int, float)) else 0.0
        if reason == "medium_term_move_review":
            r = (mf.get("return_60d") or {}).get("value")
            return abs(r) if isinstance(r, (int, float)) else 0.0
        if reason == "small_cap_low_multiple_review":
            m = (mf.get("market_cap_jpy") or {}).get("value")
            return -m if isinstance(m, (int, float)) else 0.0
        if reason == "data_conflict_review":
            return float(len((item.get("edinet_jquants_cross_check") or {}).get("mismatches") or []))
        if reason == "period_alignment_review":
            return float(len((item.get("edinet_jquants_cross_check") or {}).get("period_mismatches") or []))
        return 0.0

    buckets: dict[str, list[dict]] = {k: [] for k in reason_order}
    for item in queue_items:
        if not _is_common_equity_item(item):
            continue
        reason = _review_reason(item)
        if reason is None:
            continue
        buckets[reason].append({
            "reason": reason,
            "edinet_code": item.get("edinet_code"),
            "securities_code": (item.get("jquants_market_context") or {}).get("securities_code"),
            "_sort_value": sort_value(item, reason),
            "fact_points": _fact_points_for_item(item),
            "unknowns": _unknowns_for_item(item),
            "falsification": [
                "次決算で売上成長・利益率・自己資本比率のうち主要指標が悪化したら仮説を弱める",
                "EDINET×J-Quants の期間差/定義差が説明できなければ、判断材料から外す",
                "discipline check でサイズ/集中度/ナンピン/過熱に抵触するなら見送る",
            ],
            "next_to_read": [
                f"python3 -m radar evidence {item.get('edinet_code')} --asof <asof>",
                "直近決算短信・有価証券報告書の事業別要因",
                "J-Quants price evidence と出来高推移",
            ],
            "discipline_status": "未通過",
        })
    for reason, vals in buckets.items():
        vals.sort(key=lambda r: (-r["_sort_value"], r["edinet_code"] or ""))

    selected: list[dict] = []
    seen: set[str] = set()
    per_bucket = max(1, limit // max(1, len(reason_order)))
    for reason in sorted(reason_order, key=reason_order.get):
        for row in buckets[reason][:per_bucket]:
            key = row.get("edinet_code") or row.get("securities_code") or ""
            if key and key not in seen:
                selected.append(row)
                seen.add(key)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        remaining = [
            row for vals in buckets.values() for row in vals
            if (row.get("edinet_code") or row.get("securities_code") or "") not in seen
        ]
        remaining.sort(key=lambda r: (reason_order.get(r["reason"], 99), -r["_sort_value"], r["edinet_code"] or ""))
        for row in remaining:
            selected.append(row)
            seen.add(row.get("edinet_code") or row.get("securities_code") or "")
            if len(selected) >= limit:
                break
    for row in selected:
        row.pop("_sort_value", None)
    return selected


def build_investor_brief(*, asof: str | None = None, max_review_items: int = 10,
                         derived_root: Path | None = None) -> dict:
    """Build the daily investor brief.

    Output is a research aid for the human operator. It intentionally avoids
    trade commands, price targets, and attractiveness ordering.
    """
    if max_review_items <= 0:
        raise SystemExit("--max-review-items は正の整数で指定してください")
    if asof is not None:
        valid_asof(asof)

    from .queue import build_research_queue

    queue = build_research_queue(asof=asof, derived_root=derived_root)
    selected_asof = queue["asof"]
    jq_ctx, jq_docs = _load_jquants_docs(asof=selected_asof, derived_root=derived_root)
    jq_summary = jquants_summary(jq_ctx.get("manifest"), manifest_path=jq_ctx.get("manifest_path"))
    root = _feature_root(JQUANTS_FEATURE_SET, derived_root)
    prev_asof = _latest_before(root, selected_asof)
    previous_docs: dict[str, dict] = {}
    if prev_asof:
        _, prev_docs = _load_jquants_docs(asof=prev_asof, derived_root=derived_root)
        previous_docs = {
            d.get("securities_code"): d for d in prev_docs
            if isinstance(d.get("securities_code"), str)
        }
    return {
        "asof": selected_asof,
        "market_snapshot": _market_snapshot(jq_summary),
        "watch_changes": _watch_changes(jq_docs, previous_docs),
        "human_review_list": _human_review_list(queue["items"], limit=max_review_items),
        "source_refs": {
            "jquants_manifest": rel(jq_ctx.get("manifest_path")),
            "jquants_features": rel(jq_ctx.get("features_path")),
            "edinet_company_map_asof": (queue.get("auxiliary") or {}).get("edinet_company_map_asof"),
            "previous_jquants_asof": prev_asof,
        },
        "counts": {
            "jquants_rows": len(jq_docs),
            "research_items": len(queue["items"]),
            "human_review_items": min(max_review_items, len(_human_review_list(queue["items"], limit=max_review_items))),
        },
    }


def _render_watch_table(rows: list[dict], *, metric_key: str) -> list[str]:
    if not rows:
        return ["- 該当なし"]
    out = [
        "| code | market | sector | price_date | close | market_cap | PER | PBR | 20d | 60d | note |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        metric_note = ""
        if metric_key == "derived_day":
            metric_note = f"derived_close_change={_pct(r.get('close_change_vs_previous_derived'))}"
        elif metric_key == "small_cap":
            metric_note = "小型・低PBR/PERの形。魅力度ではなく検証入口。"
        elif metric_key == "decline":
            metric_note = "20d下落。需給/決算/一過性を確認。"
        elif metric_key == "advance":
            metric_note = "20d上昇。過熱/材料の持続性を確認。"
        out.append(
            f"| {r['securities_code']} | {r['market']} | {r['sector33']} | "
            f"{r.get('latest_price_date') or 'UNKNOWN'} | {_small_jpy(r.get('latest_close'))} | "
            f"{_small_jpy(r.get('market_cap_jpy'))} | "
            f"{'UNKNOWN' if not isinstance(r.get('per_trailing'), float) else f'{r['per_trailing']:.2f}x'} | "
            f"{'UNKNOWN' if not isinstance(r.get('pbr'), float) else f'{r['pbr']:.2f}x'} | "
            f"{_pct(r.get('return_20d'))} | {_pct(r.get('return_60d'))} | {metric_note} |"
        )
    return out


def render_investor_brief(brief: dict) -> str:
    snap = brief["market_snapshot"]
    watch = brief["watch_changes"]
    out = [
        "# Daily Investor Brief — 参謀パケット",
        "",
        f"_asof: {brief['asof']} / derived features only / raw本文・APIキーなし_",
        "",
        f"> {DISCLAIMER}",
        "",
        "## 0. 読み方",
        "- これは「今日見る論点」を固定ルールで抽出する参謀パケットです。",
        "- 売買判断ではなく、FACT/CALCULATION/INFERENCE/UNKNOWN を分けるための材料です。",
        "- すべて discipline check 未通過。最終判断は人間が行います。",
        "",
        "## 1. Market Snapshot",
        f"- latest_price_date: `{snap.get('latest_price_date') or 'UNKNOWN'}`",
        f"- listed_codes: `{snap.get('listed_codes') or 'UNKNOWN'}`",
        f"- price_coverage: `{_pct(snap.get('price_coverage_ratio'))}` / valuation_coverage: `{_pct(snap.get('valuation_coverage_ratio'))}` / market_cap_coverage: `{_pct(snap.get('market_cap_coverage_ratio'))}`",
        f"- PER trailing median: `{'UNKNOWN' if not isinstance(snap.get('per_trailing_median'), (int, float)) else f'{snap['per_trailing_median']:.2f}x'}` / PBR median: `{'UNKNOWN' if not isinstance(snap.get('pbr_median'), (int, float)) else f'{snap['pbr_median']:.2f}x'}`",
        f"- market_cap median: `{_small_jpy(snap.get('market_cap_median'))}`",
        f"- return_20d median: `{_pct(snap.get('return_20d_median'))}` / positive_rate: `{_pct(snap.get('return_20d_positive_rate'))}`",
        f"- return_60d median: `{_pct(snap.get('return_60d_median'))}` / positive_rate: `{_pct(snap.get('return_60d_positive_rate'))}`",
        f"- return_252d median: `{_pct(snap.get('return_252d_median'))}` / positive_rate: `{_pct(snap.get('return_252d_positive_rate'))}`",
        "",
        "## 2. Watch Changes",
        "### 2.1 20日下落が大きい銘柄(反証優先)",
        "- market/sector が `その他` のETF・ファンド系はこの日次表から除外。",
        *_render_watch_table(watch.get("large_declines_20d") or [], metric_key="decline"),
        "",
        "### 2.2 20日上昇が大きい銘柄(過熱確認)",
        *_render_watch_table(watch.get("large_advances_20d") or [], metric_key="advance"),
        "",
        "### 2.3 小型・低倍率の形(検証入口)",
        *_render_watch_table(watch.get("small_cap_value_shape") or [], metric_key="small_cap"),
        "",
        "### 2.4 前回derivedからの変化",
    ]
    if not watch.get("previous_derived_available"):
        out.append("- previous derived が無いため UNKNOWN")
    else:
        out.extend(_render_watch_table(watch.get("derived_day_changes") or [], metric_key="derived_day"))
    out.extend([
        "",
        "## 3. Human Review List",
        "- 抽出理由は検証入口です。魅力度・売買順ではありません。",
        "",
    ])
    reviews = brief.get("human_review_list") or []
    if not reviews:
        out.append("- 該当なし。今日は broad snapshot と既存保有の discipline 点検を優先。")
    for i, item in enumerate(reviews, start=1):
        out.extend([
            f"### {i}. {item.get('edinet_code')} / {item.get('securities_code') or 'UNKNOWN'} — {item.get('reason')}",
            "- FACT/CALCULATION:",
            *[f"  - {p}" for p in item.get("fact_points") or []],
            "- UNKNOWN / 不足:",
            *[f"  - {u}" for u in item.get("unknowns") or []],
            "- 反証条件:",
            *[f"  - {f}" for f in item.get("falsification") or []],
            "- 次に読む資料:",
            *[f"  - `{n}`" if n.startswith("python3 ") else f"  - {n}" for n in item.get("next_to_read") or []],
            "- discipline_status: 未通過",
            "",
        ])
    out.extend([
        "## 4. Source / Boundary",
        f"- J-Quants manifest: `{brief['source_refs'].get('jquants_manifest') or 'UNKNOWN'}`",
        f"- J-Quants features: `{brief['source_refs'].get('jquants_features') or 'UNKNOWN'}`",
        f"- EDINET company map asof: `{brief['source_refs'].get('edinet_company_map_asof') or 'UNKNOWN'}`",
        f"- previous J-Quants asof: `{brief['source_refs'].get('previous_jquants_asof') or 'UNKNOWN'}`",
        "- provider raw本文、APIキー、.env は含みません。",
        "- 価格目標・利益保証・将来断定はありません。",
        "",
    ])
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_investor_brief(brief: dict, *, outputs_root: Path | None = None) -> dict:
    root = outputs_root or (ROOT / "outputs")
    out_dir = root / "investor_brief"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{brief['asof']}.md"
    manifest = out_dir / f"{brief['asof']}.json"
    md.write_text(render_investor_brief(brief), encoding="utf-8")
    manifest.write_text(json.dumps({
        "asof": brief["asof"],
        "source": "derived_features_only",
        "raw_body_included": False,
        "llm_api_called": False,
        "market_snapshot": brief["market_snapshot"],
        "watch_counts": {k: len(v) if isinstance(v, list) else v for k, v in brief["watch_changes"].items()},
        "human_review_count": len(brief.get("human_review_list") or []),
        "source_refs": brief.get("source_refs") or {},
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"md_path": md, "manifest_path": manifest, "review_count": len(brief.get("human_review_list") or [])}
