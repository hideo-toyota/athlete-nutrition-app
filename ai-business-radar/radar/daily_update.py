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
    """Orchestrate features -> research-queue -> llm-brief. Best-effort per step.

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

    # 2. J-Quants bulk raw -> derived features (local only; no network/API key)
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

    summary = {"asof": asof, "item_count": 0, "calc_features": 0, "unknown_features": 0, "jquants_blocks": 0}

    # 3. research-queue (deterministic; no LLM)
    if dry_run:
        steps.append(StepResult("research-queue", "planned"))
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
        steps.append(StepResult("research-queue", "done", f"items={rq['count']}"))
    except SystemExit as e:
        steps.append(StepResult("research-queue", "skipped", str(e)))
    except Exception as e:  # noqa: BLE001
        steps.append(StepResult("research-queue", "failed", type(e).__name__))

    # 4. llm-brief (analysis-ready packet for Claude; gate confirmed)
    #    J-Quants 株価コード指定があれば、EDINET財務が無くても brief を成立させる。
    if outputs.get("research_queue_md") or jquants_codes:
        try:
            from .research import build_llm_handoff, write_llm_handoff
            packet = build_llm_handoff(asof=asof, max_items=max_items,
                                       derived_root=derived_root, jquants_codes=jquants_codes)
            lb = write_llm_handoff(packet, outputs_root=outputs_root)
            outputs["brief_md"] = str(lb["md_path"])
            summary["jquants_blocks"] = lb["jquants_count"]
            steps.append(StepResult(
                "llm-brief", "done",
                f"evidence_blocks={lb['count']} jquants_blocks={lb['jquants_count']}"))
        except SystemExit as e:
            steps.append(StepResult("llm-brief", "skipped", str(e)))
        except Exception as e:  # noqa: BLE001
            steps.append(StepResult("llm-brief", "failed", type(e).__name__))
    else:
        steps.append(StepResult("llm-brief", "skipped", "derived無しのため未生成"))

    return {"asof": asof, "dry_run": dry_run, "steps": steps, "outputs": outputs, "summary": summary}


def render_daily_summary(result: dict) -> str:
    """Discord-friendly markdown summary. Contains no raw bodies and no forbidden terms."""
    from .research.common import assert_no_forbidden_output

    s = result["summary"]
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
        f"- J-Quants 株価evidence(当時の株価): {s['jquants_blocks']} 件",
        "",
        "## Claudeに渡す分析パケット",
    ]
    brief = result["outputs"].get("brief_md")
    if brief:
        lines += [
            f"- `{brief}`",
            "- 読み方: UNKNOWN/不足 → 検証する仮説(断定しない) → 反証条件 → 次に読む資料 "
            "→ claim分類(FACT/CALCULATION/INFERENCE/ASSUMPTION/UNKNOWN) → discipline gate 注意。",
            "- 当時の株価は J-Quants block の latest_close(asof以前の調整後終値)を参照。",
            "- 禁止: 具体的な売買指示・価格目標・順位付け・利益保証・将来断定。",
        ]
    else:
        lines.append("- (今回は derived データが無く未生成。先に sync / build-features を実行)")
    text = "\n".join(lines) + "\n"
    assert_no_forbidden_output(text)
    return text
