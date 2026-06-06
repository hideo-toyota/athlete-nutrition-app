#!/usr/bin/env python3
"""Personal Equity Research Radar

自分用の「個別株・ETF 投資リサーチ／売買判断ログ」ツール。

目的:
  余剰資金で個別株・ETF を勉強しながら、自分の売買判断を構造化する。
  AI に売買を丸投げするのではなく、決算・事業・バリュエーション・リスク・反証を
  整理し、最終判断は自分で行うための「思考の足場」を作る。

使い方:
  python3 opportunity_radar.py equity   # 投資分析レポート + プロンプト集を生成(メイン)
  python3 opportunity_radar.py run      # 投資分析ワークフローの概要を出力(補助/任意)

外部 API・外部ライブラリは使いません(標準ライブラリのみ)。
リアルタイム株価取得・発注・証券会社連携はしません。手入力データで完結します。

⚠️ 重要: 本ツールは投資助言ではありません。出力の「買い候補/見送り/売却検討/継続保有」は
   あくまで自分用の整理ラベルであり、最終判断と責任は自分にあります。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"

WATCHLIST_FILE = INPUTS / "equity_watchlist.json"
OPPORTUNITIES_FILE = INPUTS / "opportunities.json"
RESEARCH_REPORT = OUTPUTS / "equity_research_report.md"
PROMPT_PACK = OUTPUTS / "equity_prompt_pack.md"
WORKFLOW_OVERVIEW = OUTPUTS / "workflow_overview.md"

# ----------------------------------------------------------------------------
# 採点軸: (key, 表示名, それを裏付ける入力フィールド群)
# 注意: 自動スコアは「ノートの充実度の目安」に過ぎず、内容の質を保証しません。
#       entry["self_scores"][key] (1-5) を入れると、その自己評価を優先します。
# ----------------------------------------------------------------------------
AXES = [
    ("business_understandability", "事業理解のしやすさ", ["business_summary", "thesis"]),
    ("growth_visibility", "売上・利益成長の確認しやすさ",
     ["latest_revenue_growth", "latest_profit_growth", "margin_trend"]),
    ("competitive_moat", "競争優位性", ["thesis", "business_summary"]),
    ("valuation_conviction", "バリュエーションの納得感", ["valuation_notes"]),
    ("kpi_trackability", "決算KPIの追跡可能性", ["kpis_to_watch", "source_notes"]),
    ("downside_clarity", "下落リスクの明確さ", ["risks", "bear_case"]),
    ("falsifiability_clarity", "反証条件の明確さ", ["exit_conditions", "bear_case"]),
    ("self_understanding", "自分の理解度", ["thesis", "business_summary", "source_notes"]),
    ("surplus_capital_fit", "余剰資金で試す妥当性", ["position_sizing"]),
    ("learning_retention", "売買後に学びが残るか", ["trade_log"]),
]
MAX_SCORE = len(AXES) * 5

DISCLAIMER = (
    "※本レポートは投資助言ではありません。特定銘柄の売買を推奨するものではなく、"
    "自分の判断を整理するためのメモです。最終判断と結果の責任は自分にあります。"
)

CAUTIONS = [
    "余剰資金の範囲で、勉強目的で行う(生活資金・必要資金は投入しない)。",
    "集中投資を避け、1銘柄あたりの投入上限を必ず決める。",
    "信用取引・レバレッジは使わない(現物のみ)。",
    "SNS等の短期的な煽り・急騰銘柄の熱量に飛びつかない。",
    "決算跨ぎは事前に方針を決め、サプライズ前提のフルポジを取らない。",
]


# ----------------------------------------------------------------------------
# 入出力ユーティリティ
# ----------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"入力ファイルが見つかりません: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"JSON の読み込みに失敗しました ({path}): {e}")


def is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    if isinstance(value, (int, float)):
        return True
    return bool(value)


def as_lines(value) -> list[str]:
    """文字列 or リストを、箇条書き用の行リストに正規化する。"""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def md_bullets(value, empty: str = "(未記入)") -> str:
    lines = as_lines(value)
    if not lines:
        return f"- {empty}"
    return "\n".join(f"- {ln}" for ln in lines)


def md_text(value, empty: str = "(未記入)") -> str:
    lines = as_lines(value)
    return " ".join(lines) if lines else empty


# ----------------------------------------------------------------------------
# 採点
# ----------------------------------------------------------------------------
def heuristic_axis_score(entry: dict, fields: list[str]) -> int:
    """裏付けフィールドの充実度から 1-5 の目安スコアを出す。"""
    filled = sum(1 for f in fields if is_filled(entry.get(f)))
    ratio = filled / len(fields) if fields else 0.0
    return max(1, round(1 + 4 * ratio))


def score_entry(entry: dict) -> dict:
    self_scores = entry.get("self_scores", {}) or {}
    axis_results = []
    total = 0
    for key, label, fields in AXES:
        heuristic = heuristic_axis_score(entry, fields)
        if key in self_scores and isinstance(self_scores[key], (int, float)):
            score = int(max(1, min(5, round(self_scores[key]))))
            origin = "自己評価"
        else:
            score = heuristic
            origin = "ノート充実度"
        total += score
        axis_results.append({"key": key, "label": label, "score": score, "origin": origin})
    return {"axes": axis_results, "total": total, "pct": total / MAX_SCORE}


def classify(entry: dict, pct: float) -> tuple[str, str]:
    """(分類ラベル, 理由) を返す。スコアは出発点であり推奨ではない。"""
    status = (entry.get("position_status") or "none").lower()
    has_falsification = is_filled(entry.get("bear_case")) or is_filled(entry.get("exit_conditions"))

    if status == "holding":
        if pct >= 0.70 and has_falsification:
            return "継続保有", "仮説が維持され、撤退条件も定義済み。継続監視で保有。"
        if pct >= 0.50:
            return "継続保有(要監視)", "仮説は概ね維持。反証条件の充実と次回決算の確認が必要。"
        return "売却検討", "ノート/仮説が弱い、または反証が積み上がっている。保有理由を再点検。"
    if status == "sold":
        return "振り返り対象", "売却済み。trade_log で学びを残し、再エントリー基準を明確化する。"
    # none
    if pct >= 0.70 and has_falsification:
        return "買い候補", "仮説・リスク・反証条件が揃い、余剰資金枠で検証する価値あり(最終判断は自分)。"
    if pct >= 0.50:
        return "様子見(リサーチ継続)", "方向性は良いが、バリュエーション/反証条件の詰めが必要。"
    return "見送り", "理解度・反証条件・リスク整理が不足。今は手を出さずリサーチを継続。"


# ----------------------------------------------------------------------------
# レポート生成
# ----------------------------------------------------------------------------
def render_policy(policy: dict) -> str:
    if not policy:
        return ""
    lines = ["## 運用ポリシー(自分ルール)", ""]
    mapping = [
        ("purpose", "目的"),
        ("max_position_per_name_jpy", "1銘柄あたり投入上限(円)"),
        ("max_loss_tolerance_per_name_pct", "1銘柄あたり最大損失許容(%)"),
        ("earnings_crossing_policy", "決算跨ぎの方針"),
        ("cautions", "注意"),
    ]
    for key, label in mapping:
        if key in policy and is_filled(policy[key]):
            lines.append(f"- **{label}**: {policy[key]}")
    lines.append("")
    return "\n".join(lines)


def render_entry(entry: dict) -> str:
    scored = score_entry(entry)
    label, reason = classify(entry, scored["pct"])

    ticker = entry.get("ticker", "----")
    name = entry.get("company_name", "(社名未記入)")
    market = entry.get("market", "")
    price = entry.get("current_price", "")
    status = entry.get("position_status", "none")

    sizing = entry.get("position_sizing", {}) or {}
    planned = sizing.get("planned_amount_jpy")
    max_loss = sizing.get("max_loss_jpy")

    out = []
    out.append(f"## {ticker} {name}")
    meta = []
    if market:
        meta.append(f"市場: {market}")
    if is_filled(price):
        meta.append(f"現在値(手入力): {price}")
    meta.append(f"ポジション: {status}")
    out.append(" / ".join(meta))
    out.append("")
    out.append(f"### 判断: **{label}**")
    out.append(f"> {reason}")
    out.append("")

    out.append("### 投資仮説")
    out.append(md_text(entry.get("thesis")))
    out.append("")
    out.append("### 事業概要")
    out.append(md_text(entry.get("business_summary")))
    out.append("")

    out.append("### 買う理由")
    out.append(md_bullets(entry.get("reason_to_buy")))
    out.append("")
    out.append("### 買わない理由 / 懸念")
    out.append(md_bullets(entry.get("reason_not_to_buy")))
    out.append("")

    out.append("### 反証条件(これが崩れたら仮説は誤り)")
    falsification = as_lines(entry.get("bear_case")) + as_lines(entry.get("exit_conditions"))
    out.append(md_bullets(falsification, empty="(未記入: bear_case / exit_conditions を埋める)"))
    out.append("")

    out.append("### 決算で見るべき KPI")
    out.append(md_bullets(entry.get("kpis_to_watch"),
                          empty="(未記入: 売上・利益・利益率・受注/会員数など追跡指標を定義する)"))
    out.append("")

    out.append("### バリュエーション確認項目")
    out.append(md_text(entry.get("valuation_notes")))
    out.append("")
    out.append("チェックリスト:")
    out.append("- [ ] PER / PBR / EV/EBITDA は同業・過去レンジと比べて割高か")
    out.append("- [ ] 成長率に対して妥当か(PEG 的視点)")
    out.append("- [ ] 期待を織り込みすぎていないか(コンセンサス比)")
    out.append("- [ ] 下振れ時にどこまで下がりうるか(弱気シナリオの株価)")
    out.append("")

    out.append("### 主なリスク")
    out.append(md_bullets(entry.get("risks")))
    out.append("")

    out.append("### シナリオ")
    out.append("**期待シナリオ(強気):**")
    out.append(md_bullets(entry.get("catalysts"), empty="(未記入: 上昇の触媒/カタリストを定義)"))
    out.append("")
    out.append("**弱気シナリオ:**")
    out.append(md_text(entry.get("bear_case"), empty="(未記入: 何が起きると下落するか)"))
    out.append("")
    out.append("**撤退条件:**")
    out.append(md_bullets(entry.get("exit_conditions"),
                          empty="(未記入: 価格・ファンダの撤退ラインを定義)"))
    out.append("")

    out.append("### ポジションサイジング")
    if is_filled(planned):
        out.append(f"- 予定投入額: {planned} 円")
    if is_filled(max_loss):
        out.append(f"- 最大損失許容: {max_loss} 円")
    if not is_filled(planned) and not is_filled(max_loss):
        out.append("- (未記入: 投入上限と最大損失を先に決める)")
    out.append("")

    # スコア表
    out.append("### スコア(目安)")
    out.append(f"合計 **{scored['total']} / {MAX_SCORE}**(充実度 {scored['pct']*100:.0f}%)")
    out.append("")
    out.append("| 採点軸 | スコア | 根拠 |")
    out.append("|---|---|---|")
    for ax in scored["axes"]:
        out.append(f"| {ax['label']} | {ax['score']}/5 | {ax['origin']} |")
    out.append("")
    out.append("> スコアは「リサーチの整理度」の目安です。内容の正しさを保証しません。"
               "`self_scores` に 1-5 で自己評価を入れると、その値を優先します。")
    out.append("")

    # 振り返りログ
    out.append("### 売買後の振り返りログ")
    trade_log = entry.get("trade_log") or []
    if trade_log:
        out.append("| 日付 | アクション | なぜ | 結果 | 学び |")
        out.append("|---|---|---|---|---|")
        for t in trade_log:
            out.append("| {date} | {action} | {reason} | {result} | {lesson} |".format(
                date=t.get("date", ""), action=t.get("action", ""),
                reason=t.get("reason", ""), result=t.get("result", ""),
                lesson=t.get("lesson", "")))
    else:
        out.append("(まだ記録なし。売買したら『なぜ買ったか/売ったか/結果から何を学んだか』を残す)")
    out.append("")
    out.append("source_notes: " + md_text(entry.get("source_notes"), empty="(出典未記入)"))
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


def render_summary_table(entries: list[dict]) -> str:
    rows = ["## サマリー", "", "| ティッカー | 銘柄 | ポジション | 判断 | 充実度 |",
            "|---|---|---|---|---|"]
    for entry in entries:
        scored = score_entry(entry)
        label, _ = classify(entry, scored["pct"])
        rows.append("| {t} | {n} | {p} | {l} | {pct:.0f}% |".format(
            t=entry.get("ticker", ""), n=entry.get("company_name", ""),
            p=entry.get("position_status", "none"), l=label, pct=scored["pct"] * 100))
    rows.append("")
    return "\n".join(rows)


def build_research_report(data: dict) -> str:
    entries = data.get("watchlist", [])
    policy = data.get("policy", {})
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [
        "# Personal Equity Research Radar — 投資リサーチ・判断ログ",
        "",
        f"_生成日時: {now} / 銘柄数: {len(entries)}_",
        "",
        f"> {DISCLAIMER}",
        "",
        "### 余剰資金・勉強目的の心得",
        "\n".join(f"- {c}" for c in CAUTIONS),
        "",
        render_policy(policy),
        render_summary_table(entries),
        "---",
        "",
    ]
    for entry in entries:
        parts.append(render_entry(entry))
    parts.append(f"> {DISCLAIMER}")
    parts.append("")
    return "\n".join(p for p in parts if p is not None)


# ----------------------------------------------------------------------------
# プロンプト集生成
# ----------------------------------------------------------------------------
def build_prompt_pack(data: dict) -> str:
    entries = data.get("watchlist", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        "# Equity Prompt Pack — AI に深掘り/振り返りを頼むためのプロンプト集",
        "",
        f"_生成日時: {now}_",
        "",
        "AI に丸投げするためではなく、自分の論点を埋めるための問いです。"
        "回答は鵜呑みにせず、一次情報(決算短信・有報・適時開示)で必ず裏取りする。",
        "",
        f"> {DISCLAIMER}",
        "",
        "---",
        "",
    ]
    for entry in entries:
        ticker = entry.get("ticker", "----")
        name = entry.get("company_name", "")
        thesis = md_text(entry.get("thesis"), empty="(仮説未記入)")
        parts.append(f"## {ticker} {name}")
        parts.append("")
        parts.append("### ① 仮説の壁打ち(リサーチ深掘り)")
        parts.append("```")
        parts.append(f"私は {ticker} {name} に次の投資仮説を持っています:")
        parts.append(f"仮説: {thesis}")
        parts.append("この仮説について、以下を断定せず・推奨せずに整理してください:")
        parts.append("1. この事業を1段深く理解するための質問を5つ")
        parts.append("2. 仮説が成立する前提条件と、それを確認できる一次情報")
        parts.append("3. 直近の売上・利益・利益率トレンドで確認すべき点")
        parts.append("4. 競争優位性(モート)があるとすれば何で、どう崩れうるか")
        parts.append("5. バリュエーションが割高/割安かを判断するための観点")
        parts.append("6. 強気・弱気それぞれのシナリオと、その分岐点となる事実")
        parts.append("※結論として『買え/売れ』とは言わないでください。論点整理に徹してください。")
        parts.append("```")
        parts.append("")
        parts.append("### ② 反証(あえて弱気で叩く)")
        parts.append("```")
        parts.append(f"{ticker} {name} について、私の仮説を否定する『最も説得力のある弱気論』を")
        parts.append("構築してください。次を含めてください:")
        parts.append("- 仮説が間違っていた場合に最初に観測されるサイン")
        parts.append("- この銘柄を今は買わない/売るべき合理的な理由")
        parts.append("- 撤退すべき定量的な条件(価格・ファンダ)の案")
        parts.append("```")
        parts.append("")
        parts.append("### ③ 決算チェック(決算発表後に使う)")
        parts.append("```")
        parts.append(f"{ticker} {name} の最新決算について、私が事前に定めた KPI:")
        kpis = ", ".join(as_lines(entry.get("kpis_to_watch"))) or "(KPI 未定義 — まず定義する)"
        parts.append(f"KPI: {kpis}")
        parts.append("これらが前年比/前四半期比でどう変化したかを整理し、")
        parts.append("当初仮説が『強化された/中立/弱まった』のどれかを根拠付きで判定してください。")
        parts.append("```")
        parts.append("")
        parts.append("### ④ 売買後の振り返り(トレード記録用)")
        parts.append("```")
        parts.append(f"{ticker} {name} を売買しました。次の3点を私が書くので、")
        parts.append("感情と事実を分け、次に活かせる学びとして1段抽象化してください:")
        parts.append("- なぜ買ったか / なぜ売ったか:")
        parts.append("- 結果(損益・想定との差):")
        parts.append("- この経験から得た再現性のある学び:")
        parts.append("また、同じ失敗を避けるためのチェック項目を1つ提案してください。")
        parts.append("```")
        parts.append("")
        parts.append("---")
        parts.append("")
    parts.append(f"> {DISCLAIMER}")
    parts.append("")
    return "\n".join(parts)


# ----------------------------------------------------------------------------
# コマンド
# ----------------------------------------------------------------------------
def cmd_equity() -> None:
    data = load_json(WATCHLIST_FILE)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    RESEARCH_REPORT.write_text(build_research_report(data), encoding="utf-8")
    PROMPT_PACK.write_text(build_prompt_pack(data), encoding="utf-8")
    n = len(data.get("watchlist", []))
    print(f"投資分析レポートを生成しました ({n} 銘柄):")
    print(f"  - {RESEARCH_REPORT.relative_to(ROOT)}")
    print(f"  - {PROMPT_PACK.relative_to(ROOT)}")


def cmd_run() -> None:
    data = load_json(OPPORTUNITIES_FILE)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# {data.get('workflow_name', '投資分析ワークフロー')}", "",
             f"_生成日時: {now}_", "", data.get("purpose", ""), ""]
    for step in data.get("steps", []):
        lines.append(f"## {step.get('phase', '')}")
        for a in step.get("actions", []):
            lines.append(f"- {a}")
        lines.append("")
    if data.get("principles"):
        lines.append("## 原則")
        for p in data["principles"]:
            lines.append(f"- {p}")
        lines.append("")
    lines.append(f"> {DISCLAIMER}")
    WORKFLOW_OVERVIEW.write_text("\n".join(lines), encoding="utf-8")
    print(f"ワークフロー概要を生成しました: {WORKFLOW_OVERVIEW.relative_to(ROOT)}")
    print("（投資分析のメインは `python3 opportunity_radar.py equity`）")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Equity Research Radar — 自分用の投資リサーチ・判断ログ")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("equity", help="投資分析レポート + プロンプト集を生成(メイン)")
    sub.add_parser("run", help="投資分析ワークフローの概要を出力(補助)")
    args = parser.parse_args()

    if args.command == "equity":
        cmd_equity()
    elif args.command == "run":
        cmd_run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
