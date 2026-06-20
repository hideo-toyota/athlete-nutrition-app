"""Build a local research queue from derived features.

This does not rank attractiveness and does not create trade ideas.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .common import (
    DISCLAIMER,
    assert_no_forbidden_output,
    jquants_market_context,
    jquants_summary,
    load_edinet_company_map,
    load_feature_docs,
    load_jquants_context,
    metric_value,
    rel,
)


def _feature(doc: dict, key: str) -> dict:
    return (doc.get("features") or {}).get(key) or {}


def _status(doc: dict, key: str) -> str:
    return str(_feature(doc, key).get("status") or "UNKNOWN")


def _pct(value) -> str:
    return "UNKNOWN" if not isinstance(value, (int, float)) else f"{value * 100:.1f}%"


def _risks(doc: dict) -> list[str]:
    risks = []
    for key in ("valuation_status", "roic_proxy"):
        if _status(doc, key) == "UNKNOWN":
            risks.append(f"{key}=UNKNOWN")
    if _status(doc, "revenue_growth_yoy") == "CALCULATION":
        v = _feature(doc, "revenue_growth_yoy").get("value")
        if isinstance(v, (int, float)) and v < 0:
            risks.append("revenue_growth_yoy<0")
    if _status(doc, "operating_margin") == "CALCULATION":
        v = _feature(doc, "operating_margin").get("value")
        if isinstance(v, (int, float)) and v < 0:
            risks.append("operating_margin<0")
    if _status(doc, "net_cash") == "CALCULATION":
        v = _feature(doc, "net_cash").get("value")
        if isinstance(v, (int, float)) and v < 0:
            risks.append("net_cash<0")
    return risks or ["no_risk_flag_from_available_features"]


def _market_risk(market_context: dict) -> list[str]:
    if market_context.get("status") != "matched":
        return ["jquants_price_context=UNKNOWN"]
    risks = []
    for key in ("return_20d", "return_60d", "return_252d"):
        m = (market_context.get("features") or {}).get(key) or {}
        v = m.get("value")
        if isinstance(v, (int, float)) and v < 0:
            risks.append(f"{key}<0")
    return risks


def _item(doc: dict, market_context: dict | None = None) -> dict:
    features = doc.get("features") or {}
    unknown = sorted(k for k, v in features.items() if isinstance(v, dict) and v.get("status") == "UNKNOWN")
    calculated = sorted(k for k, v in features.items() if isinstance(v, dict) and v.get("status") == "CALCULATION")
    code = doc.get("edinet_code") or "UNKNOWN"
    market_context = market_context or {"status": "UNKNOWN", "features": {}}
    evidence_refs = [{
        "derived_path": rel(doc.get("_path")),
        "feature_set": doc.get("feature_set"),
        "raw_hash_normalized": (doc.get("input") or {}).get("raw_hash_normalized"),
        "raw_hash_compressed": (doc.get("input") or {}).get("raw_hash_compressed"),
    }]
    if market_context.get("evidence_ref"):
        evidence_refs.append(market_context["evidence_ref"])
    return {
        "type": "research_item",
        "entity_id": code,
        "edinet_code": code,
        "ticker": market_context.get("securities_code") or "UNKNOWN",
        "company_name": "UNKNOWN",
        "market": market_context.get("market") or "UNKNOWN",
        "sector": market_context.get("sector33") or "UNKNOWN",
        "liquidity": "UNKNOWN",
        "data_freshness": {
            "asof": doc.get("asof"),
            "available_at": (doc.get("input") or {}).get("available_at"),
            "retrieved_at": (doc.get("input") or {}).get("retrieved_at"),
            "jquants_asof": market_context.get("jquants_asof"),
            "latest_price_date": market_context.get("latest_price_date"),
        },
        "extraction_reason_id": "screen:edinet_financials_feature_review_v1",
        "evidence_refs": evidence_refs,
        "computed_features": calculated,
        "unknown_features": unknown,
        "key_risks": _risks(doc) + _market_risk(market_context),
        "jquants_market_context": market_context,
        "falsification": [
            "次回同じfeature_setでUNKNOWNが増えたら、根拠不足として保留する",
            "revenue_growth_yoy / operating_margin / net_margin のいずれかが悪化したら、仮説を再点検する",
            "J-Quants price context が未結合、または短中期リターンが悪化したら、市場側の仮説を再点検する",
        ],
        "next_to_read": [
            "EDINET financials raw/provenance",
            "次回決算の同一feature_set",
            "J-Quants local derived price context",
            "時価総額/発行済株式数 dataset は未取得のため valuation_status は UNKNOWN",
        ],
        "discipline_status": "未通過",
        "coverage_priority": 0,
        "claim_tags": {
            "features": "CALCULATION",
            "jquants_market_context": market_context.get("claim", "UNKNOWN"),
            "unknowns": "UNKNOWN",
            "risks": "INFERENCE(CALCULATION依存)",
        },
        "disclaimer": "調査項目。売買指示ではない。売買は discipline check + 人間判断が必要。",
    }


def build_research_queue(*, asof: str | None = None, derived_root: Path | None = None) -> dict:
    asof, docs = load_feature_docs(asof=asof, derived_root=derived_root)
    company_map = load_edinet_company_map(asof=asof, derived_root=derived_root)
    jquants = load_jquants_context(asof=asof, derived_root=derived_root)
    items = [_item(d, jquants_market_context(d, jquants=jquants, company_map=company_map)) for d in docs]
    items.sort(key=lambda x: x["edinet_code"])
    return {
        "asof": asof,
        "items": items,
        "auxiliary": {
            "edinet_company_map_asof": company_map.get("asof"),
            "jquants_summary": jquants_summary(jquants.get("manifest"), manifest_path=jquants.get("manifest_path")),
        },
    }


def render_research_queue(queue: dict) -> str:
    out = [
        "# Research Queue — 調査項目(売買指示なし)",
        "",
        f"_asof: {queue['asof']} / type は research_item 固定 / discipline_status は未通過固定_",
        "",
        f"> {DISCLAIMER}",
        "",
        "| edinet_code | sec_code | price_date | close | per | pbr | 20d | 60d | CALCULATION | UNKNOWN | key_risks | evidence |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in queue["items"]:
        mc = item.get("jquants_market_context") or {}
        mf = mc.get("features") or {}
        out.append(
            f"| {item['edinet_code']} | {mc.get('securities_code') or 'UNKNOWN'} | "
            f"{mc.get('latest_price_date') or 'UNKNOWN'} | {metric_value(mf.get('latest_close') or {})} | "
            f"{metric_value(mf.get('per_trailing') or {})} | {metric_value(mf.get('pbr') or {})} | "
            f"{metric_value(mf.get('return_20d') or {})} | {metric_value(mf.get('return_60d') or {})} | "
            f"{len(item['computed_features'])} | {len(item['unknown_features'])} | "
            f"{'; '.join(item['key_risks'])} | `python3 -m radar evidence {item['edinet_code']} --asof {queue['asof']}` |"
        )
    out.extend([
        "",
        "## J-Quants local context",
    ])
    summary = (queue.get("auxiliary") or {}).get("jquants_summary") or {}
    coverage = summary.get("coverage") or {}
    if summary.get("status") == "CALCULATION":
        out.extend([
            f"- feature_set: `{summary.get('feature_set')}` / asof: `{summary.get('asof')}`",
            f"- latest_price_date: `{coverage.get('latest_price_date')}`",
            f"- price_coverage: `{_pct(coverage.get('price_coverage_ratio'))}` / summary_coverage: `{_pct(coverage.get('summary_coverage_ratio'))}`",
        ])
    else:
        out.append("- J-Quants local features: UNKNOWN")
    out.extend([
        "",
        "## 注意",
        "- 並べ替えは edinet_code のみ。魅力度・売買順ではありません。",
        "- J-Quants price context は調査の時点確認用です。魅力度・売買順ではありません。",
        "- per/pbr は J-Quants trailing(直近本決算ベース・予想PERではない)。EDINET由来 valuation_status は別途 UNKNOWN。",
        "- 第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用・再配布/公開なし)。",
        "",
    ])
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_research_queue(queue: dict, *, outputs_root: Path | None = None) -> dict:
    root = outputs_root or (Path(__file__).resolve().parent.parent.parent / "outputs")
    root.mkdir(parents=True, exist_ok=True)
    md = root / "research_queue.md"
    csv_path = root / "research_queue.csv"
    md.write_text(render_research_queue(queue), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "edinet_code", "extraction_reason_id", "calculation_count",
                    "unknown_count", "securities_code", "latest_price_date", "latest_close",
                    "per_trailing", "pbr", "return_20d", "return_60d",
                    "discipline_status", "evidence_command"])
        for item in queue["items"]:
            mc = item.get("jquants_market_context") or {}
            mf = mc.get("features") or {}
            w.writerow([
                item["type"], item["edinet_code"], item["extraction_reason_id"],
                len(item["computed_features"]), len(item["unknown_features"]),
                mc.get("securities_code"),
                mc.get("latest_price_date"),
                (mf.get("latest_close") or {}).get("value"),
                (mf.get("per_trailing") or {}).get("value"),
                (mf.get("pbr") or {}).get("value"),
                (mf.get("return_20d") or {}).get("value"),
                (mf.get("return_60d") or {}).get("value"),
                item["discipline_status"],
                f"python3 -m radar evidence {item['edinet_code']} --asof {queue['asof']}",
            ])
    return {"md_path": md, "csv_path": csv_path, "count": len(queue["items"])}
