"""Render local evidence packs from derived features."""
from __future__ import annotations

from pathlib import Path

from .common import (
    DISCLAIMER,
    assert_no_forbidden_output,
    edinet_jquants_cross_check,
    format_pct,
    jquants_market_context,
    load_edinet_company_map,
    load_feature_doc,
    load_jquants_context,
    metric_value,
    rel,
    valid_edinet_code,
)
from .queue import _item


FEATURE_ORDER = (
    "revenue_growth_yoy",
    "operating_margin",
    "net_margin",
    "roe_proxy",
    "roic_proxy",
    "fcf_proxy",
    "net_cash",
    "equity_ratio",
    "valuation_status",
)


def build_evidence(entity: str, *, asof: str | None = None, derived_root: Path | None = None) -> dict:
    asof, doc = load_feature_doc(entity, asof=asof, derived_root=derived_root)
    company_map = load_edinet_company_map(asof=asof, derived_root=derived_root)
    jquants = load_jquants_context(asof=asof, derived_root=derived_root)
    market_context = jquants_market_context(doc, jquants=jquants, company_map=company_map)
    cross_check = edinet_jquants_cross_check(doc, market_context)
    return {
        "asof": asof,
        "doc": doc,
        "item": _item(doc, market_context),
        "jquants_market_context": market_context,
        "edinet_jquants_cross_check": cross_check,
    }


def render_evidence(evidence: dict) -> str:
    doc = evidence["doc"]
    item = evidence["item"]
    features = doc.get("features") or {}
    input_meta = doc.get("input") or {}
    out = [
        f"# Evidence — {doc.get('edinet_code')} financial features",
        "",
        f"_asof: {evidence['asof']} / feature_set: {doc.get('feature_set')} / discipline_status: 未通過_",
        "",
        f"> {DISCLAIMER}",
        "",
        "## 鮮度・由来 [FACT]",
        f"- derived: `{rel(doc.get('_path'))}`",
        f"- available_at: `{input_meta.get('available_at')}` / retrieved_at: `{input_meta.get('retrieved_at')}`",
        f"- raw_hash_normalized: `{input_meta.get('raw_hash_normalized')}`",
        f"- raw_hash_compressed: `{input_meta.get('raw_hash_compressed')}`",
        "",
        "## feature 一覧 [CALCULATION/UNKNOWN]",
        "| feature | status | value | unit | source_fields | claim |",
        "|---|---|---:|---|---|---|",
    ]
    for key in FEATURE_ORDER:
        m = features.get(key) or {}
        claim = "UNKNOWN" if m.get("status") == "UNKNOWN" else "CALCULATION"
        out.append(
            f"| {key} | {m.get('status', 'UNKNOWN')} | {metric_value(m)} | "
            f"{m.get('unit') or ''} | {', '.join(m.get('source_fields') or [])} | {claim} |"
        )
    mc = evidence.get("jquants_market_context") or {}
    mf = mc.get("features") or {}
    out.extend([
        "",
        "## J-Quants market/price context [CALCULATION/UNKNOWN]",
    ])
    if mc.get("status") == "matched":
        out.extend([
            f"- securities_code: `{mc.get('securities_code')}`",
            f"- feature_set/asof: `{mc.get('feature_set')}` / `{mc.get('jquants_asof')}`",
            f"- latest_price_date: `{mc.get('latest_price_date')}`",
            f"- latest_close: `{metric_value(mf.get('latest_close') or {})}`",
            f"- latest_volume: `{metric_value(mf.get('latest_volume') or {})}`",
            f"- shares_outstanding: `{metric_value(mf.get('shares_outstanding') or {})}`",
            f"- market_cap_jpy: `{metric_value(mf.get('market_cap_jpy') or {})}`  (latest_close×shares_outstanding; PIT proxy)",
            f"- per_trailing: `{metric_value(mf.get('per_trailing') or {})}`  (trailing・予想PERではない)",
            f"- pbr: `{metric_value(mf.get('pbr') or {})}`",
            f"- eps_trailing: `{metric_value(mf.get('eps_trailing') or {})}`",
            f"- bps: `{metric_value(mf.get('bps') or {})}`",
            f"- return_20d: `{metric_value(mf.get('return_20d') or {})}`",
            f"- return_60d: `{metric_value(mf.get('return_60d') or {})}`",
            f"- return_252d: `{metric_value(mf.get('return_252d') or {})}`",
            f"- dividend_record_present: `{metric_value(mf.get('dividend_record_present') or {})}`",
            f"- derived_ref: `{(mc.get('evidence_ref') or {}).get('derived_path')}`",
            f"- input_manifest_digest: `{(mc.get('evidence_ref') or {}).get('input_manifest_digest')}`",
        ])
    else:
        out.extend([
            "- securities_code: `UNKNOWN`",
            f"- reason: `{mc.get('reason')}`",
            f"- J-Quants feature asof: `{mc.get('jquants_asof')}` / company_map_asof: `{mc.get('company_map_asof')}`",
        ])
    cross = evidence.get("edinet_jquants_cross_check") or {}
    out.extend([
        "",
        "## EDINET vs J-Quants cross-check [CALCULATION/UNKNOWN]",
    ])
    if cross.get("status") == "CALCULATION":
        out.extend([
            "| metric | EDINET | J-Quants | delta | tolerance | result |",
            "|---|---:|---:|---:|---:|---|",
        ])
        for row in cross.get("checks") or []:
            result = (
                "period_mismatch"
                if row.get("within_tolerance") is None
                else ("within_tolerance" if row.get("within_tolerance") else "mismatch")
            )
            out.append(
                f"| {row['edinet_feature']} ↔ {row['jquants_feature']} | "
                f"{format_pct(row.get('edinet_value'))} | {format_pct(row.get('jquants_value'))} | "
                f"{format_pct(row.get('delta')).replace('%', 'pt')} | "
                f"{format_pct(row.get('tolerance')).replace('%', 'pt')} | {result} |"
            )
    else:
        out.append(f"- status: `UNKNOWN` / reason: `{cross.get('reason')}`")
    out.extend([
        "",
        "## 主要リスク/不足 [INFERENCE/UNKNOWN]",
    ])
    for r in item["key_risks"]:
        out.append(f"- {r}")
    out.extend([
        "",
        "## 反証条件 [INFERENCE]",
    ])
    for f in item["falsification"]:
        out.append(f"- {f}")
    out.extend([
        "",
        "## 次に読むもの [UNKNOWNを減らすため]",
    ])
    for n in item["next_to_read"]:
        out.append(f"- {n}")
    out.extend([
        "",
        "## discipline gate 雛形",
        "- 売買を考える場合でも、先に `python3 -m radar check buy <TICKER> <AMOUNT_JPY> <SECTOR>` を通す。",
        "- `<TICKER>` / `<AMOUNT_JPY>` / `<SECTOR>` は人間が別途入力するプレースホルダです。具体金額の提案ではありません。",
        "",
        "## claim tags",
        "- features: CALCULATION",
        "- J-Quants market/price context: CALCULATION/UNKNOWN",
        "- EDINET vs J-Quants cross-check: CALCULATION/UNKNOWN",
        "- missing/固定UNKNOWN: UNKNOWN",
        "- key_risks/falsification: INFERENCE(CALCULATION依存)",
        "",
        "> この evidence は provider raw 本文を含みません。第三者LLM入力は LICENSE_MATRIX E5/J5 本人確認 2026-06-20 済(個人の私的分析利用)。",
        "",
    ])
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_evidence(evidence: dict, *, outputs_root: Path | None = None) -> dict:
    code = valid_edinet_code(evidence["doc"].get("edinet_code"))
    root = outputs_root or (Path(__file__).resolve().parent.parent.parent / "outputs")
    out_dir = root / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{code}.md"
    p.write_text(render_evidence(evidence), encoding="utf-8")
    return {"path": p, "edinet_code": code}
