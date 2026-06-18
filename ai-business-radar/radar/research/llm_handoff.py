"""Build a bounded LLM handoff packet from local derived evidence.

This creates the packet to feed into an LLM. It does not call any LLM API.
"""
from __future__ import annotations

import json
from pathlib import Path

from .common import DISCLAIMER, assert_no_forbidden_output
from .evidence import build_evidence, render_evidence
from .queue import build_research_queue, render_research_queue


def build_llm_handoff(*, asof: str | None = None, derived_root: Path | None = None, max_items: int | None = None) -> dict:
    queue = build_research_queue(asof=asof, derived_root=derived_root)
    items = queue["items"][:max_items] if max_items is not None else queue["items"]
    evidence_blocks = []
    for item in items:
        ev = build_evidence(item["edinet_code"], asof=queue["asof"], derived_root=derived_root)
        evidence_blocks.append(render_evidence(ev))
    return {"asof": queue["asof"], "queue": queue, "evidence_blocks": evidence_blocks}


def render_llm_handoff(packet: dict) -> str:
    out = [
        "# LLM Brief — daily research packet",
        "",
        f"_asof: {packet['asof']} / input: derived features + local evidence only_",
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
        "## Research queue",
        render_research_queue(packet["queue"]),
        "",
        "## Evidence blocks",
    ]
    for i, block in enumerate(packet["evidence_blocks"], start=1):
        out.extend(["", f"### Evidence block {i}", block])
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
    manifest.write_text(json.dumps({
        "asof": packet["asof"],
        "item_count": len(packet["queue"]["items"]),
        "evidence_count": len(packet["evidence_blocks"]),
        "source": "derived_features_and_local_evidence_only",
        "raw_body_included": False,
        "llm_api_called": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"md_path": md, "manifest_path": manifest, "count": len(packet["evidence_blocks"])}
