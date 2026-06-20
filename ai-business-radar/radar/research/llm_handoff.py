"""Build a bounded LLM handoff packet from local derived evidence.

This creates the packet to feed into an LLM. It does not call any LLM API.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import DISCLAIMER, assert_no_forbidden_output
from .evidence import build_evidence, render_evidence
from .jquants_evidence import build_jquants_evidence, render_jquants_evidence
from .queue import build_research_queue, render_research_queue


def build_llm_handoff(*, asof: str | None = None, derived_root: Path | None = None,
                      max_items: int | None = None, jquants_codes: list[str] | None = None) -> dict:
    # J-Quants price evidence (PIT). Built first so an EDINET-less run can still
    # produce a price-only brief (the user's "当時の株価で判断" path).
    jquants_blocks = []
    jq_asof = None
    for code in jquants_codes or []:
        ev = build_jquants_evidence(code, asof=asof, derived_root=derived_root)
        jq_asof = ev["asof"]
        jquants_blocks.append(render_jquants_evidence(ev))

    try:
        queue = build_research_queue(asof=asof, derived_root=derived_root)
    except SystemExit:
        if not jquants_codes:
            raise
        # EDINET財務が無くても J-Quants 株価だけで brief を成立させる
        queue = {"asof": asof or jq_asof or "UNKNOWN", "items": []}

    items = queue["items"][:max_items] if max_items is not None else queue["items"]
    evidence_blocks = []
    for item in items:
        ev = build_evidence(item["edinet_code"], asof=queue["asof"], derived_root=derived_root)
        evidence_blocks.append(render_evidence(ev))
    return {
        "asof": queue["asof"],
        "queue": queue,
        "evidence_blocks": evidence_blocks,
        "jquants_blocks": jquants_blocks,
        "jquants_summary": (queue.get("auxiliary") or {}).get("jquants_summary"),
    }


def _pct(value) -> str:
    return "UNKNOWN" if not isinstance(value, (int, float)) else f"{value * 100:.1f}%"


def _render_jquants_summary(summary: dict | None) -> list[str]:
    summary = summary or {}
    out = [
        "## J-Quants market context",
    ]
    if summary.get("status") != "CALCULATION":
        return out + [
            "- J-Quants local features: UNKNOWN",
            "- 個別証券コードとの結合が無い場合、evidence 側も UNKNOWN として扱う。",
            "",
        ]
    coverage = summary.get("coverage") or {}
    dist = summary.get("distribution") or {}
    out.extend([
        f"- feature_set/asof: `{summary.get('feature_set')}` / `{summary.get('asof')}`",
        f"- latest_price_date: `{coverage.get('latest_price_date')}`",
        f"- price_coverage: `{_pct(coverage.get('price_coverage_ratio'))}` / summary_coverage: `{_pct(coverage.get('summary_coverage_ratio'))}`",
        f"- return_20d median: `{_pct((dist.get('return_20d') or {}).get('median'))}` / positive_rate: `{_pct((dist.get('return_20d') or {}).get('positive_rate'))}`",
        f"- return_60d median: `{_pct((dist.get('return_60d') or {}).get('median'))}` / positive_rate: `{_pct((dist.get('return_60d') or {}).get('positive_rate'))}`",
        f"- return_252d median: `{_pct((dist.get('return_252d') or {}).get('median'))}` / positive_rate: `{_pct((dist.get('return_252d') or {}).get('positive_rate'))}`",
        f"- derived_ref: `{summary.get('derived_path')}`",
        "- 用途: 市場/価格文脈の確認。売買順・魅力度順ではない。",
        "",
    ])
    return out


def render_llm_handoff(packet: dict) -> str:
    out = [
        "# LLM Brief — daily research packet",
        "",
        f"_asof: {packet['asof']} / input: derived features + local evidence only_",
        "",
        "> LICENSE_MATRIX E5/J5(第三者LLM入力)= 本人確認 2026-06-20(個人の私的分析利用・第三者再配布/公開なし)。"
        "このpacketは Claude 等に渡して分析してよい。raw一括再配布・公開は引き続き禁止。",
        "",
        f"> {DISCLAIMER}",
        "",
        "## LLM task",
        "- 目的: 数値の事実整理、弱点の洗い出し、反証条件、次に読む資料を短く整理する。",
        "- 禁止: 具体的な売買指示、価格目標、順位付け、利益保証、将来断定。",
        "- 必須: FACT / CALCULATION / INFERENCE / ASSUMPTION / UNKNOWN を混ぜない。",
        "- 必須: UNKNOWN と反証条件を先に出す。",
        "- 必須: 最終判断は人間、discipline check 未通過と明記する。",
        "",
        "## Required response shape",
        "1. UNKNOWN / 不足",
        "2. 検証対象の仮説(断定しない)",
        "3. 反証条件",
        "4. 次に読む資料",
        "5. claim分類表",
        "6. discipline gate 注意",
        "",
        *_render_jquants_summary(packet.get("jquants_summary")),
        "## Research queue",
        render_research_queue(packet["queue"]),
        "",
        "## Evidence blocks",
    ]
    for i, block in enumerate(packet["evidence_blocks"], start=1):
        out.extend(["", f"### Evidence block {i}", block])
    if packet.get("jquants_blocks"):
        out.extend(["", "## J-Quants price evidence (PIT・当時の株価)"])
        for i, block in enumerate(packet["jquants_blocks"], start=1):
            out.extend(["", f"### J-Quants block {i}", block])
    out.extend([
        "",
        "## Handoff boundary",
        "- provider raw本文、APIキー、.env は含まない。",
        "- このpacketの内容は derived/evidence の範囲に限定。",
        "- 外部LLMへ送る運用では、会話ログ側にも秘密情報を貼らない。",
        "",
    ])
    text = "\n".join(out)
    assert_no_forbidden_output(text)
    return text


def write_llm_handoff(packet: dict, *, outputs_root: Path | None = None) -> dict:
    root = outputs_root or (Path(__file__).resolve().parent.parent.parent / "outputs")
    out_dir = root / "llm_handoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / f"{packet['asof']}.md"
    manifest = out_dir / f"{packet['asof']}.json"
    md.write_text(render_llm_handoff(packet), encoding="utf-8")
    jquants_blocks = packet.get("jquants_blocks") or []
    manifest.write_text(json.dumps({
        "asof": packet["asof"],
        "item_count": len(packet["queue"]["items"]),
        "evidence_count": len(packet["evidence_blocks"]),
        "jquants_block_count": len(jquants_blocks),
        "jquants_context_status": (packet.get("jquants_summary") or {}).get("status", "UNKNOWN"),
        "jquants_feature_asof": (packet.get("jquants_summary") or {}).get("asof"),
        "source": "derived_features_and_local_evidence_only",
        "raw_body_included": False,
        "llm_api_called": False,
        "third_party_llm_gate": "LICENSE_MATRIX_E5_J5_CONFIRMED_2026-06-20",
        "analysis_cleared": True,
        "analysis_basis": "personal_private_use_no_redistribution",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"md_path": md, "manifest_path": manifest,
            "count": len(packet["evidence_blocks"]), "jquants_count": len(jquants_blocks)}
