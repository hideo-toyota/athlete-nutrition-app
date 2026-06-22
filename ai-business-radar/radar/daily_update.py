"""`radar daily-update` — one-shot daily research pipeline for Discord operation.

Runs the local analysis pipeline end to end and produces an analysis-ready
handoff brief for Claude to read and reason over via Discord.

Discipline (unchanged):
- Does NOT call any LLM API here. Claude reads the produced brief separately.
- Does NOT place trades, and never emits buy candidates / rankings / predictions.
- raw bodies and API key values are never printed.

Third-party LLM input gate:
- LICENSE_MATRIX E5/J5 を 2026-06-20 に本人確認(個人の私的分析利用・第三者への
  再配布や公開なし・Anthropic は処理委託先)。これにより derived/evidence/brief を
  Claude に渡して分析させる運用が解禁された。raw 一括再配布・公開は引き続き禁止。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LICENSE_GATE = (
    "LICENSE_MATRIX E5/J5 本人確認(2026-06-20)済: "
    "個人の私的分析利用・第三者再配布/公開なし・Anthropicは処理委託先"
)


@dataclass
class StepResult:
    name: str
    status: str  # done / skipped / failed / planned
    detail: str = ""

    def line(self) -> str:
        mark = {"done": "✅", "skipped": "⏭️", "failed": "⚠️", "planned": "•"}.get(self.status, "•")
        tail = f" — {self.detail}" if self.detail else ""
        return f"{mark} {self.name}: {self.status}{tail}"


def _today() -> str:
    return date.today().isoformat()


def _edinet_raw_dir(root: Path, asof: str) -> Path:
    return root / "data" / "raw" / "edinet-db" / "financials" / asof


def _edinet_company_raw_dir(root: Path, asof: str) -> Path:
    return root / "data" / "raw" / "edinet-db" / "companies" / asof


def _existing_company_map_asof(root: Path, derived_root: Path | None, asof: str) -> str | None:
    """Return a usable existing company-map asof, if any.

    Company master data is slower-moving than financials. A daily run should not
    look broken just because today's companies raw was not re-synced, as long as
    an older derived map at-or-before asof is available.
    """
    from .research.common import EDINET_COMPANY_MAP_FEATURE_SET, latest_asof_at_or_before

    base = (derived_root or (root / "data" / "derived")) / "features" / EDINET_COMPANY_MAP_FEATURE_SET
    selected = latest_asof_at_or_before(base, asof)
    if selected and (base / selected / "companies.jsonl").exists():
        return selected
    return None


def _jquants_bulk_dir(root: Path) -> Path:
    return root / "data" / "raw" / "jquants" / "bulk"


def run_daily_update(
    *,
    asof: str | None = None,
    max_items: int | None = None,
    build_edinet: bool = True,
    build_jquants: bool = True,
    jquants_codes: list[str] | None = None,
    dry_run: bool = False,
    root: Path | None = None,
    derived_root: Path | None = None,
    outputs_root: Path | None = None,
) -> dict:
    """Orchestrate features -> research-queue -> investor-brief -> llm-brief.

    Each step is isolated: a missing input is `skipped`, an error is `failed`,
    and the run continues so the operator gets a full status in one shot.
    """
    root = root or ROOT
    asof = asof or _today()
    steps: list[StepResult] = [StepResult("license-gate", "done", LICENSE_GATE)]
    outputs: dict = {}

    # 1. EDINET financials raw -> derived features
    edinet_dir = _edinet_raw_dir(root, asof)
    if not build_edinet:
        steps.append(StepResult("build-features(edinet)", "skipped", "--no-edinet"))
    elif not edinet_dir.exists():
        steps.append(StepResult("build-features(edinet)", "skipped", f"raw無し: {edinet_dir}"))
    elif dry_run:
        steps.append(StepResult("build-features(edinet)", "planned", f"raw_dir={edinet_dir}"))
    else:
        try:
            from .features import build_financial_features_batch
            res = build_financial_features_batch(raw_dir=str(edinet_dir), asof=asof, limit=None)
            steps.append(StepResult(
                "build-features(edinet)", "done",
                f"built={res['built_count']} failures={res['failure_count']}"))
        except SystemExit as e:
            steps.append(StepResult("build-features(edinet)", "failed", str(e)))
        except Exception as e:  # noqa: BLE001 - never leak raw; report type only
            steps.append(StepResult("build-features(edinet)", "failed", type(e).__name__))

    # 2. EDINET companies raw -> derived code map. This bridge lets EDINET
    #    financial items carry J-Quants price context in research/evidence.
    company_dir = _edinet_company_raw_dir(root, asof)
    if not build_edinet:
        steps.append(StepResult("build-company-map(edinet)", "skipped", "--no-edinet"))
    elif not company_dir.exists():
        existing = _existing_company_map_asof(root, derived_root, asof)
        if existing:
            steps.append(StepResult(
                "build-company-map(edinet)", "done",
                f"既存map使用(asof={existing})。当日companies raw無し: {company_dir}",
            ))
        else:
            steps.append(StepResult("build-company-map(edinet)", "skipped", f"companies raw無し: {company_dir}"))
    elif dry_run:
        steps.append(StepResult("build-company-map(edinet)", "planned", f"raw_dir={company_dir}"))
    else:
        try:
            from .features import build_edinet_company_map
            res = build_edinet_company_map(
                raw_dir=str(company_dir),
                asof=asof,
                raw_root=root / "data" / "raw",
                derived_root=derived_root,
            )
            steps.append(StepResult(
                "build-company-map(edinet)", "done",
                f"rows={res['row_count']} mapped={res['mapped_securities_code_count']}"))
        except SystemExit as e:
            steps.append(StepResult("build-company-map(edinet)", "failed", str(e)))
        except Exception as e:  # noqa: BLE001
            steps.append(StepResult("build-company-map(edinet)", "failed", type(e).__name__))

    # 3. J-Quants bulk raw -> derived features (local only; no network/API key)
    jq_dir = _jquants_bulk_dir(root)
    if not build_jquants:
        steps.append(StepResult("build-features(jquants)", "skipped", "--no-jquants"))
    elif not jq_dir.exists():
        steps.append(StepResult("build-features(jquants)", "skipped", f"bulk無し: {jq_dir}"))
    elif dry_run:
        steps.append(StepResult("build-features(jquants)", "planned", f"bulk_dir={jq_dir}"))
    else:
        try:
            from .features import build_jquants_bulk_features
            res = build_jquants_bulk_features(asof=asof)
            steps.append(StepResult("build-features(jquants)", "done", f"rows={res['feature_rows']}"))
        except SystemExit as e:
            steps.append(StepResult("build-features(jquants)", "failed", str(e)))
        except Exception as e:  # noqa: BLE001
            steps.append(StepResult("build-features(jquants)", "failed", type(e).__name__))

    summary = {
        "asof": asof,
        "item_count": 0,
        "calc_features": 0,
        "unknown_features": 0,
        "jquants_context_status": "UNKNOWN",
        "jquants_latest_price_date": None,
        "jquants_price_coverage_ratio": None,
        "jquants_valuation_coverage_ratio": None,
        "jquants_blocks": 0,
        "human_review_items": 0,
    }

    # 4. research-queue (deterministic; no LLM)
    if dry_run:
        steps.append(StepResult("research-queue", "planned"))
        steps.append(StepResult("investor-brief", "planned"))
        steps.append(StepResult("llm-brief", "planned"))
        return {"asof": asof, "dry_run": dry_run, "steps": steps, "outputs": outputs, "summary": summary}

    queue = None
    try:
        from .research import build_research_queue, write_research_queue
        queue = build_research_queue(asof=asof, derived_root=derived_root)
        rq = write_research_queue(queue, outputs_root=outputs_root)
        outputs["research_queue_md"] = str(rq["md_path"])
        summary["item_count"] = rq["count"]
        summary["calc_features"] = sum(len(i["computed_features"]) for i in queue["items"])
        summary["unknown_features"] = sum(len(i["unknown_features"]) for i in queue["items"])
        jq_summary = ((queue.get("auxiliary") or {}).get("jquants_summary") or {})
        jq_coverage = jq_summary.get("coverage") or {}
        summary["jquants_context_status"] = jq_summary.get("status", "UNKNOWN")
        summary["jquants_latest_price_date"] = jq_coverage.get("latest_price_date")
        summary["jquants_price_coverage_ratio"] = jq_coverage.get("price_coverage_ratio")
        summary["jquants_valuation_coverage_ratio"] = jq_coverage.get("valuation_coverage_ratio")
        steps.append(StepResult("research-queue", "done", f"items={rq['count']}"))
    except SystemExit as e:
        steps.append(StepResult("research-queue", "skipped", str(e)))
    except Exception as e:  # noqa: BLE001
        steps.append(StepResult("research-queue", "failed", type(e).__name__))

    # 5. investor-brief (human daily operating packet; no LLM/API).
    #    Works on J-Quants alone (Market Snapshot/Watch Changes); the builder
    #    skips cleanly only when neither EDINET nor J-Quants derived exists.
    try:
        from .research import build_investor_brief, write_investor_brief
        ib = build_investor_brief(asof=asof, max_review_items=max_items or 10, derived_root=derived_root)
        ib_res = write_investor_brief(ib, outputs_root=outputs_root)
        outputs["investor_brief_md"] = str(ib_res["md_path"])
        summary["human_review_items"] = ib_res["review_count"]
        steps.append(StepResult("investor-brief", "done", f"human_review_items={ib_res['review_count']}"))
    except SystemExit as e:
        steps.append(StepResult("investor-brief", "skipped", str(e)))
    except Exception as e:  # noqa: BLE001
        steps.append(StepResult("investor-brief", "failed", type(e).__name__))

    # 6. llm-brief (analysis-ready packet for Claude; gate confirmed)
    #    J-Quants 株価コード指定があれば、EDINET財務が無くても brief を成立させる。
    if outputs.get("research_queue_md") or jquants_codes:
        try:
            from .research import build_llm_handoff, write_llm_handoff
            packet = build_llm_handoff(asof=asof, max_items=max_items,
                                       derived_root=derived_root, jquants_codes=jquants_codes)
            lb = write_llm_handoff(packet, outputs_root=outputs_root)
            outputs["brief_md"] = str(lb["md_path"])
            prompt = write_discord_prompt(result_like={
                "asof": asof,
                "brief_md": _display_path(lb["md_path"]),
                "investor_brief_md": (
                    _display_path(outputs["investor_brief_md"])
                    if outputs.get("investor_brief_md") else None
                ),
                "evidence_count": lb["count"],
                "jquants_count": lb["jquants_count"],
            }, outputs_root=outputs_root)
            outputs["discord_prompt_md"] = str(prompt["path"])
            summary["jquants_blocks"] = lb["jquants_count"]
            steps.append(StepResult(
                "llm-brief", "done",
                f"evidence_blocks={lb['count']} jquants_blocks={lb['jquants_count']}"))
            steps.append(StepResult("discord-prompt", "done", str(prompt["path"])))
        except SystemExit as e:
            steps.append(StepResult("llm-brief", "skipped", str(e)))
        except Exception as e:  # noqa: BLE001
            steps.append(StepResult("llm-brief", "failed", type(e).__name__))
    else:
        steps.append(StepResult("llm-brief", "skipped", "derived無しのため未生成"))

    return {"asof": asof, "dry_run": dry_run, "steps": steps, "outputs": outputs, "summary": summary}


def render_discord_prompt(*, asof: str, brief_md: str, evidence_count: int, jquants_count: int,
                          investor_brief_md: str | None = None) -> str:
    """Short prompt to paste into Discord/Claude Code.

    It references the local handoff file instead of pasting the whole packet.
    No provider raw body, API key, or env value is included.
    """
    from .research.common import assert_no_forbidden_output

    lines = [
        f"# Discord LLM Prompt — {asof}",
        "",
        "以下のローカル分析packetを読み、投資助言ではなく調査メモとして要約してください。",
        "",
        f"- investor_brief: `{investor_brief_md}`" if investor_brief_md else "- investor_brief: `UNKNOWN`",
        f"- packet: `{brief_md}`",
        f"- evidence_blocks: {evidence_count}",
        f"- jquants_blocks: {jquants_count}",
        "",
        "必須ルール:",
        "- まず UNKNOWN / 不足データを列挙する。",
        "- investor_brief の Market Snapshot / Watch Changes / Human Review List を優先して読む。",
        "- FACT / CALCULATION / INFERENCE / ASSUMPTION / UNKNOWN を分ける。",
        "- 検証対象の仮説、反証条件、次に読む資料を短く出す。",
        "- discipline check 未通過であり、最終判断は人間と明記する。",
        "- 売買指示、価格目標、順位付け、利益保証、将来断定は禁止。",
        "- provider raw本文、APIキー、.env、認証情報を要求しない。",
        "",
        "出力形式:",
        "1. UNKNOWN / 不足",
        "2. 検証対象の仮説(断定しない)",
        "3. 反証条件",
        "4. 次に読む資料",
        "5. claim分類表",
        "6. discipline gate 注意",
        "",
    ]
    text = "\n".join(lines)
    assert_no_forbidden_output(text)
    return text


def write_discord_prompt(*, result_like: dict, outputs_root: Path | None = None) -> dict:
    root = outputs_root or (ROOT / "outputs")
    out_dir = root / "discord"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"llm_prompt_{result_like['asof']}.md"
    path.write_text(render_discord_prompt(
        asof=result_like["asof"],
        brief_md=result_like["brief_md"],
        investor_brief_md=result_like.get("investor_brief_md"),
        evidence_count=result_like["evidence_count"],
        jquants_count=result_like["jquants_count"],
    ), encoding="utf-8")
    return {"path": path}


def _display_path(path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except (OSError, ValueError):
        return str(p)


def render_daily_summary(result: dict) -> str:
    """Discord-friendly markdown summary. Contains no raw bodies and no forbidden terms."""
    from .research.common import assert_no_forbidden_output

    s = result["summary"]
    coverage = s.get("jquants_price_coverage_ratio")
    coverage_text = f"{coverage * 100:.1f}%" if isinstance(coverage, (int, float)) else "UNKNOWN"
    valuation_coverage = s.get("jquants_valuation_coverage_ratio")
    valuation_coverage_text = (
        f"{valuation_coverage * 100:.1f}%" if isinstance(valuation_coverage, (int, float)) else "UNKNOWN"
    )
    title = f"# Daily Update — {result['asof']}" + ("  (dry-run)" if result["dry_run"] else "")
    lines = [
        title,
        "",
        f"> {LICENSE_GATE}",
        "> これは調査用の整理。投資助言・売買指示・順位・予測ではありません。最終判断は人間。",
        "",
        "## ステップ",
    ]
    lines += [f"- {st.line()}" for st in result["steps"]]
    lines += [
        "",
        "## サマリ",
        f"- research_item: {s['item_count']} 件",
        f"- CALCULATION features: {s['calc_features']} / UNKNOWN features: {s['unknown_features']}",
        f"- J-Quants 市場コンテキスト: {s.get('jquants_context_status', 'UNKNOWN')}"
        f" / latest_price_date={s.get('jquants_latest_price_date') or 'UNKNOWN'}"
        f" / price_coverage={coverage_text} / valuation_coverage={valuation_coverage_text}",
        f"- J-Quants 単独evidence(--jquants-codes指定時): {s['jquants_blocks']} 件",
        "",
        "## Claudeに渡す分析パケット",
    ]
    investor = result["outputs"].get("investor_brief_md")
    if investor:
        lines += [
            f"- 今日読む参謀パケット: `{_display_path(investor)}`",
            f"- human review list: {s.get('human_review_items', 0)} 件"
            "（見る理由/FACT/UNKNOWN/反証/次に読む資料。売買指示ではない）",
            "",
        ]
    brief = result["outputs"].get("brief_md")
    if brief:
        lines += [
            f"- `{_display_path(brief)}`",
            "- 読み方: UNKNOWN/不足 → 検証する仮説(断定しない) → 反証条件 → 次に読む資料 "
            "→ claim分類(FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN) → discipline gate 注意。",
            "- 当時の株価は research/evidence 内の J-Quants market context、または"
            " --jquants-codes 指定時の J-Quants block の latest_close(asof以前の調整後終値)を参照。",
            "- 禁止: 具体的な売買指示・価格目標・順位付け・利益保証・将来断定。",
        ]
        prompt = result["outputs"].get("discord_prompt_md")
        if prompt:
            lines += [
                "",
                "## Discordに貼る短い指示",
                f"- `{_display_path(prompt)}`",
                "- この短い指示を貼ると、Claude側は上記packetを読む前提で、禁止事項と出力形式を固定できる。",
            ]
    else:
        lines.append("- (今回は derived データが無く未生成。先に sync / build-features を実行)")
    text = "\n".join(lines) + "\n"
    assert_no_forbidden_output(text)
    return text
