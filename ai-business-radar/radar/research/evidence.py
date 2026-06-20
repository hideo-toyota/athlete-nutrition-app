"""Render local evidence packs from derived features."""
from __future__ import annotations

from pathlib import Path

from .common import DISCLAIMER, assert_no_forbidden_output, load_feature_doc, metric_value, rel, valid_edinet_code
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
    return {"asof": asof, "doc": doc, "item": _item(doc)}


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
