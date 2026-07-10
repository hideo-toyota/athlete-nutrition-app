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
import csv as csv_module
import json
import sys
from datetime import datetime
from pathlib import Path

import ohlcv_data
import trend_backtest as bt
import trend_indicators as ti

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
OUTPUTS = ROOT / "outputs"

WATCHLIST_FILE = INPUTS / "equity_watchlist.json"
OPPORTUNITIES_FILE = INPUTS / "opportunities.json"
RESEARCH_REPORT = OUTPUTS / "equity_research_report.md"
PROMPT_PACK = OUTPUTS / "equity_prompt_pack.md"
WORKFLOW_OVERVIEW = OUTPUTS / "workflow_overview.md"
TREND_REPORT = OUTPUTS / "trend_report.md"
TREND_RANKING = OUTPUTS / "trend_ranking.csv"
TRADE_JOURNAL_PROMPTS = OUTPUTS / "trade_journal_prompts.md"
TREND_BACKTEST_REPORT = OUTPUTS / "trend_backtest_report.md"
OBSIDIAN_DIR = OUTPUTS / "obsidian"

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


# ----------------------------------------------------------------------------
# trend コマンド: 上昇トレンド分析
# ----------------------------------------------------------------------------
def fpct(x, plus=True):
    if x is None:
        return "—"
    return f"{x*100:+.1f}%" if plus else f"{x*100:.1f}%"


def fnum(x):
    if x is None:
        return "—"
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:.2f}"


def yesno(b):
    return "○" if b else "×"


def trend_assessment(entry: dict, r: dict, bt_params: dict) -> dict:
    """レポートに必ず含める項目を生成して返す。"""
    m, score, label = r["m"], r["score"], r["label"]
    w = ti.DEFAULTS["ma_windows"]
    ma = m["ma"]
    stop = bt_params.get("stop_loss_pct", bt.DEFAULTS["stop_loss_pct"])
    exit_th = bt_params.get("exit_threshold", bt.DEFAULTS["exit_threshold"])

    why = [a for a, _ in r["adds"]] or ["明確な上昇根拠は乏しい"]

    invalidation = [
        f"20日線({fnum(ma[w[0]])})を終値で明確に下回る",
        "60日線が下向きに転換する",
        f"60日線({fnum(ma[w[1]])})を割り込む",
        "ベンチマーク相対リターンがマイナスに転じる",
    ]

    if label == "過熱注意":
        wait = ["20日線近辺までの押し目を待つ", "急騰の出来高が落ち着き、再度出来高を伴って上抜けるのを確認"]
    elif label == "押し目監視":
        wait = ["20日線の回復+陽線での反発を確認", "直近高値の更新に出来高が伴うか確認"]
    elif label in ("強い上昇トレンド", "上昇トレンド候補"):
        wait = ["押し目(20日線タッチ)での分割エントリー", "直近高値ブレイク+出来高増の確認"]
    else:
        wait = ["トレンド転換(20日線>60日線かつ両者が上向き)を確認してから"]

    not_buy = [s for s, _ in r["subs"]]
    if label in ("下落トレンド", "レンジ") and not not_buy:
        not_buy = ["明確な上昇トレンドが確認できない"]

    exits = [
        f"取得価格から -{stop*100:.0f}% で損切り",
        "60日線を終値で明確に割れたら撤退",
        f"トレンドスコアが {exit_th} 未満に低下したら縮小/撤退",
    ]

    dte = m.get("days_to_earnings")
    if dte is None:
        earnings = "次回決算日が未入力(next_earnings_date を埋めると跨ぎリスクを表示)"
    elif dte < 0:
        earnings = f"直近決算は {abs(dte)} 日前。決算反応の出尽くし/織り込みに注意"
    elif m.get("earnings_crossing_risk"):
        earnings = f"決算まであと {dte} 日。跨ぎリスク高。ポジションを抑える/見送る判断を"
    else:
        earnings = f"決算まであと {dte} 日。直前はサイズ調整を検討"

    rel = m.get("rel_return")
    if rel is None:
        rel_text = "ベンチマーク相対リターンが計算できない(データ不足)"
    elif rel > 0.05:
        rel_text = f"ベンチ比 {fpct(rel)} と明確に強い。市場平均を上回っている"
    elif rel > 0:
        rel_text = f"ベンチ比 {fpct(rel)} とやや強い。優位性は限定的"
    else:
        rel_text = f"ベンチ比 {fpct(rel)} で市場平均より弱い。トレンドの質に注意"

    heat = None
    if entry.get("material_or_pts"):
        heat = {
            "熱量(短期の盛り上がり)": [
                f"出来高20日平均比: {fnum(m.get('volume_ratio'))}倍",
                f"直近の急騰(押し目なし): {yesno(m.get('spike_no_pullback'))}",
                f"ストップ高水準の単日変動(代理): {yesno(m.get('limit_up_proxy'))}",
                f"20日線からの乖離: {fpct(m.get('dist_from_ma20'))}",
            ],
            "継続トレンド(構造)": [
                f"20>60>120日線の並び: {yesno(ma[w[0]] and ma[w[1]] and ma[w[2]] and ma[w[0]]>ma[w[1]]>ma[w[2]])}",
                f"60日線の傾き: {fpct(m['slope'][w[1]])}",
                f"60日リターン: {fpct(m['returns'][w[1]])}",
            ],
            "note": "材料/PTS急騰は『熱量』が先行しがち。継続トレンド(MA構造・中期リターン)が伴うまで本格判断は保留。",
        }

    return {"why": why, "invalidation": invalidation, "wait": wait,
            "not_buy": not_buy, "exits": exits, "earnings": earnings,
            "rel_text": rel_text, "heat": heat}


def build_trend_report(results: list[dict], bench: list, data_cfg: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ok = [r for r in results if r["ok"]]
    bench_name = data_cfg.get("benchmark_name", "ベンチマーク")
    parts = [
        "# 上昇トレンド分析レポート (trend)",
        "",
        f"_生成日時: {now} / 銘柄数: {len(results)} / ベンチマーク: {bench_name}_",
        "",
        f"> {DISCLAIMER}",
        "> 上昇トレンドは「当たる手法」ではありません。余剰資金で市場平均を上回れるかを検証し、最終判断は自分で行うための整理です。",
        "",
        "### 心得",
        "\n".join(f"- {c}" for c in CAUTIONS),
        "",
        "## ランキング(トレンドスコア順)",
        "",
        "| 銘柄 | 判断 | スコア | 終値 | ベンチ比60d | 20d/60d/120d超 | 出来高比 | 過熱度 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(ok, key=lambda x: x["score"], reverse=True):
        m, e = r["m"], r["entry"]
        w = ti.DEFAULTS["ma_windows"]
        above = f"{yesno(m['above_ma'][w[0]])}/{yesno(m['above_ma'][w[1]])}/{yesno(m['above_ma'][w[2]])}"
        parts.append("| {tk} {nm} | {lb} | {sc} | {cl} | {rel} | {ab} | {vr}倍 | {oh} |".format(
            tk=e.get("ticker", ""), nm=e.get("company_name", ""), lb=r["label"], sc=r["score"],
            cl=fnum(m["close"]), rel=fpct(m.get("rel_return")), ab=above,
            vr=fnum(m.get("volume_ratio")), oh=fpct(m.get("dist_from_ma20"))))
    parts.append("")
    skipped = [r for r in results if not r["ok"]]
    if skipped:
        parts.append("> データ不足でスキップ: " +
                     ", ".join(f"{r['entry'].get('ticker','?')}({r['source']})" for r in skipped))
        parts.append("")
    parts.append("---\n")

    for r in sorted(ok, key=lambda x: x["score"], reverse=True):
        parts.append(render_trend_entry(r))
    parts.append(f"> {DISCLAIMER}")
    parts.append("")
    return "\n".join(parts)


def render_trend_entry(r: dict) -> str:
    e, m = r["entry"], r["m"]
    w = ti.DEFAULTS["ma_windows"]
    a = trend_assessment(e, r, r["bt_params"])
    o = []
    o.append(f"## {e.get('ticker','')} {e.get('company_name','')}")
    o.append(f"データ源: {r['source']} / 基準日: {m['date']} / 終値: {fnum(m['close'])}")
    o.append("")
    o.append(f"### 判断: **{r['label']}**(トレンドスコア {r['score']}/100)")
    o.append(f"- ベンチ比(60d): {fpct(m.get('rel_return'))} / 出来高20日平均比: {fnum(m.get('volume_ratio'))}倍 "
             f"/ 過熱度(20MA乖離): {fpct(m.get('dist_from_ma20'))}")
    o.append("")

    o.append("### なぜ上昇トレンドと判定したか")
    o.append("\n".join(f"- {x}" for x in a["why"]))
    o.append("")
    o.append("### どこが崩れたら仮説が否定されるか(反証条件)")
    o.append("\n".join(f"- {x}" for x in a["invalidation"]))
    o.append("")
    o.append("### 買うならどの条件を待つか")
    o.append("\n".join(f"- {x}" for x in a["wait"]))
    o.append("")
    o.append("### 買わない理由 / 減点要因")
    o.append("\n".join(f"- {x}" for x in a["not_buy"]) if a["not_buy"] else "- (目立った減点要因なし)")
    o.append("")
    o.append("### 損切り・撤退条件")
    o.append("\n".join(f"- {x}" for x in a["exits"]))
    o.append("")
    o.append("### 決算前後の注意点")
    o.append(f"- {a['earnings']}")
    o.append("")
    o.append("### 市場平均と比べて本当に強いか")
    o.append(f"- {a['rel_text']}")
    o.append("")

    if a["heat"]:
        o.append("### 熱量 vs 継続トレンド(材料株/PTS急騰)")
        for k in ("熱量(短期の盛り上がり)", "継続トレンド(構造)"):
            o.append(f"**{k}**")
            o.append("\n".join(f"- {x}" for x in a["heat"][k]))
        o.append(f"> {a['heat']['note']}")
        o.append("")

    o.append("### 主要指標")
    o.append("| 指標 | 値 |")
    o.append("|---|---|")
    rows = [
        ("20/60/120日線", f"{fnum(m['ma'][w[0]])} / {fnum(m['ma'][w[1]])} / {fnum(m['ma'][w[2]])}"),
        ("20日線の傾き / 60日線の傾き", f"{fpct(m['slope'][w[0]])} / {fpct(m['slope'][w[1]])}"),
        ("終値 > 20/60/120日線", f"{yesno(m['above_ma'][w[0]])}/{yesno(m['above_ma'][w[1]])}/{yesno(m['above_ma'][w[2]])}"),
        ("20日高値からの距離", fpct(m['dist_high'].get(w[0]))),
        ("60日高値からの距離", fpct(m['dist_high'].get(w[1]))),
        ("年初来高値からの距離", fpct(m.get('dist_ytd_high'))),
        ("20/60/120日リターン", f"{fpct(m['returns'][w[0]])} / {fpct(m['returns'][w[1]])} / {fpct(m['returns'][w[2]])}"),
        ("ベンチ相対リターン(60d)", fpct(m.get('rel_return'))),
        ("出来高20日平均比", f"{fnum(m.get('volume_ratio'))}倍"),
        ("売買代金20日平均", fnum(m.get('turnover_20'))),
        ("ATR / ATR比率", f"{fnum(m.get('atr'))} / {fpct(m.get('atr_pct'), plus=False)}"),
        ("20日値幅率", fpct(m.get('range_pct'), plus=False)),
        ("最大ドローダウン(120d)", fpct(m.get('max_drawdown'))),
        ("決算まで日数", str(m.get('days_to_earnings')) if m.get('days_to_earnings') is not None else "—"),
        ("ストップ高/安(代理)", f"{yesno(m.get('limit_up_proxy'))}/{yesno(m.get('limit_down_proxy'))}"),
    ]
    for k, v in rows:
        o.append(f"| {k} | {v} |")
    o.append("")
    o.append("---")
    o.append("")
    return "\n".join(o)


def write_trend_ranking(results: list[dict]) -> None:
    w = ti.DEFAULTS["ma_windows"]
    headers = ["ticker", "company_name", "label", "score", "close", "rel_return_60",
               "ret_20", "ret_60", "ret_120", "above_20", "above_60", "above_120",
               "slope_20", "slope_60", "dist_ma20", "volume_ratio", "turnover_20",
               "atr_pct", "max_drawdown_120", "days_to_earnings"]
    with TREND_RANKING.open("w", newline="", encoding="utf-8") as f:
        wr = csv_module.writer(f)
        wr.writerow(headers)
        for r in sorted((x for x in results if x["ok"]),
                        key=lambda x: x["score"], reverse=True):
            m, e = r["m"], r["entry"]
            wr.writerow([
                e.get("ticker", ""), e.get("company_name", ""), r["label"], r["score"],
                round(m["close"], 2), _r(m.get("rel_return")),
                _r(m["returns"][w[0]]), _r(m["returns"][w[1]]), _r(m["returns"][w[2]]),
                int(m["above_ma"][w[0]]), int(m["above_ma"][w[1]]), int(m["above_ma"][w[2]]),
                _r(m["slope"][w[0]]), _r(m["slope"][w[1]]), _r(m.get("dist_from_ma20")),
                _r(m.get("volume_ratio"), 2), round(m.get("turnover_20") or 0),
                _r(m.get("atr_pct")), _r(m.get("max_drawdown")),
                m.get("days_to_earnings") if m.get("days_to_earnings") is not None else "",
            ])


def _r(x, nd=4):
    return round(x, nd) if isinstance(x, (int, float)) else ""


def build_trade_journal_prompts(results: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        "# Trade Journal Prompts — 売買判断・振り返り用プロンプト",
        "",
        f"_生成日時: {now}_",
        "",
        "AI に売買を委ねるためではなく、自分の判断を言語化し、後で検証するための問いです。",
        f"> {DISCLAIMER}",
        "",
        "---",
        "",
    ]
    for r in sorted((x for x in results if x["ok"]), key=lambda x: x["score"], reverse=True):
        e, m = r["entry"], r["m"]
        tk, nm = e.get("ticker", ""), e.get("company_name", "")
        parts.append(f"## {tk} {nm}(判断: {r['label']} / スコア {r['score']})")
        parts.append("")
        parts.append("### エントリー前チェック")
        parts.append("```")
        parts.append(f"{tk} {nm} の上昇トレンド判定は「{r['label']}」、スコア{r['score']}、")
        parts.append(f"ベンチ相対(60d){fpct(m.get('rel_return'))}、出来高比{fnum(m.get('volume_ratio'))}倍。")
        parts.append("この状況で、断定せずに次を整理してください:")
        parts.append("1. このトレンドが本物である根拠と、ダマシである可能性")
        parts.append("2. 市場平均を上回っていると言える条件は満たされているか")
        parts.append("3. いま買うのか、押し目を待つのか。待つなら具体的な価格/条件")
        parts.append("4. 損切りライン・撤退条件の妥当性")
        parts.append("5. 決算など、近くにあるイベントリスク")
        parts.append("※『買え/売れ』ではなく、判断材料の整理に徹してください。")
        parts.append("```")
        parts.append("")
        parts.append("### 売買後の振り返り")
        parts.append("```")
        parts.append(f"{tk} {nm} を売買しました。感情と事実を分けて、再現性のある学びに整理してください。")
        parts.append("- なぜ買ったか:")
        parts.append("- なぜ売ったか:")
        parts.append("- 結果(損益・想定との差):")
        parts.append("- 学び:")
        parts.append("- 次回改善:")
        parts.append("```")
        parts.append("")
        parts.append("---")
        parts.append("")
    return "\n".join(parts)


def build_obsidian_note(r: dict) -> str:
    e, m = r["entry"], r["m"]
    a = trend_assessment(e, r, r["bt_params"])
    tk, nm = e.get("ticker", ""), e.get("company_name", "")
    log = e.get("trade_log") or []
    last = log[-1] if log else {}
    lines = [
        f"# {nm} / {tk}",
        "",
        "## 今日の判断",
        f"- 判断: {r['label']}",
        f"- 理由: {'; '.join(a['why'])}",
        f"- 上昇トレンドスコア: {r['score']}/100",
        f"- ベンチマーク比: {fpct(m.get('rel_return'))}",
        f"- 出来高: {fnum(m.get('volume_ratio'))}倍(20日平均比)",
        f"- 過熱度: {fpct(m.get('dist_from_ma20'))}(20日線乖離)",
        "",
        "## 買う理由",
        "\n".join(f"- {x}" for x in (e.get("reason_to_buy") or a["why"]))
        if (e.get("reason_to_buy") or a["why"]) else "- ",
        "",
        "## 買わない理由",
        "\n".join(f"- {x}" for x in a["not_buy"]) if a["not_buy"] else "- ",
        "",
        "## 反証条件",
        "\n".join(f"- {x}" for x in a["invalidation"]),
        "",
        "## 撤退条件",
        "\n".join(f"- {x}" for x in a["exits"]),
        "",
        "## 決算で確認すること",
        "\n".join(f"- {x}" for x in (e.get("kpis_to_watch") or [])) if e.get("kpis_to_watch") else f"- {a['earnings']}",
        "",
        "## 売買後の振り返り",
        f"- なぜ買ったか: {last.get('reason','')}",
        "- なぜ売ったか: ",
        f"- 結果: {last.get('result','')}",
        f"- 学び: {last.get('lesson','')}",
        "- 次回改善: ",
        "",
        f"> {DISCLAIMER}",
        "",
    ]
    return "\n".join(lines)


def cmd_trend() -> None:
    data = load_json(WATCHLIST_FILE)
    data_cfg = data.get("data_source", {})
    trend_params = data.get("trend_params", {})
    bt_params = data.get("backtest", {})
    bench = ohlcv_data.load_benchmark(data_cfg)
    entries = data.get("watchlist", [])

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for entry in entries:
        bars, source = ohlcv_data.load_prices(entry, data_cfg)
        m = ti.compute_indicators(bars, bench, trend_params) if bars else None
        if m is None:
            results.append({"entry": entry, "source": source, "ok": False})
            continue
        ti.attach_earnings(m, entry.get("next_earnings_date"))
        score, adds, subs = ti.trend_score(m, trend_params)
        results.append({
            "entry": entry, "source": source, "ok": True, "m": m,
            "score": score, "adds": adds, "subs": subs,
            "label": ti.trend_label(m, score, trend_params), "bt_params": bt_params,
        })

    TREND_REPORT.write_text(build_trend_report(results, bench, data_cfg), encoding="utf-8")
    write_trend_ranking(results)
    TRADE_JOURNAL_PROMPTS.write_text(build_trade_journal_prompts(results), encoding="utf-8")
    for r in results:
        if r["ok"]:
            (OBSIDIAN_DIR / f"{r['entry'].get('ticker','UNKNOWN')}.md").write_text(
                build_obsidian_note(r), encoding="utf-8")

    ok_n = sum(1 for r in results if r["ok"])
    print(f"トレンド分析を生成しました ({ok_n}/{len(results)} 銘柄):")
    print(f"  - {TREND_REPORT.relative_to(ROOT)}")
    print(f"  - {TREND_RANKING.relative_to(ROOT)}")
    print(f"  - {TRADE_JOURNAL_PROMPTS.relative_to(ROOT)}")
    print(f"  - {OBSIDIAN_DIR.relative_to(ROOT)}/<ticker>.md")


# ----------------------------------------------------------------------------
# backtest-trend コマンド
# ----------------------------------------------------------------------------
def _fmt_metrics(label: str, mtr: dict) -> list[str]:
    if mtr.get("trades", 0) == 0:
        return [f"**{label}**: 取引なし"]
    return [
        f"**{label}**(取引{mtr['trades']}回)",
        f"- 勝率: {mtr['win_rate']*100:.1f}% / 平均利益: {fpct(mtr['avg_win'])} / 平均損失: {fpct(mtr['avg_loss'])}",
        f"- 累積リターン(複利): {fpct(mtr['total_return'])} / 最大DD: {fpct(mtr['max_drawdown'])}",
        f"- シャープ(取引ベース): {mtr['sharpe_per_trade']:.2f} / PF: "
        f"{mtr['profit_factor']:.2f}" if mtr.get('profit_factor') else
        f"- シャープ(取引ベース): {mtr['sharpe_per_trade']:.2f} / PF: —",
        f"- 平均保有日数: {mtr['avg_hold_days']:.1f}日",
    ]


def cmd_backtest_trend() -> None:
    data = load_json(WATCHLIST_FILE)
    data_cfg = data.get("data_source", {})
    trend_params = data.get("trend_params", {})
    bt_params = data.get("backtest", {})
    bench = ohlcv_data.load_benchmark(data_cfg)
    entries = data.get("watchlist", [])
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [
        "# トレンド・シグナル バックテスト (backtest-trend)",
        "",
        f"_生成日時: {now}_",
        "",
        f"> {DISCLAIMER}",
        "> シグナル発生の翌営業日に執行、未来データ不使用、手数料+スリッページ控除。"
        "学習期間と検証期間(アウトオブサンプル)に分けて集計しています。"
        "過去の結果は将来を保証せず、過剰最適化に注意してください。",
        "",
        f"前提: エントリー={bt_params.get('entry', bt.DEFAULTS['entry'])} / "
        f"買いスコア≥{bt_params.get('entry_threshold', bt.DEFAULTS['entry_threshold'])} / "
        f"手仕舞いスコア<{bt_params.get('exit_threshold', bt.DEFAULTS['exit_threshold'])} / "
        f"損切り{bt_params.get('stop_loss_pct', bt.DEFAULTS['stop_loss_pct'])*100:.0f}% / "
        f"利確{bt_params.get('take_profit_pct', bt.DEFAULTS['take_profit_pct'])*100:.0f}% / "
        f"最大保有{bt_params.get('hold_max_days', bt.DEFAULTS['hold_max_days'])}日 / "
        f"片道コスト{(bt_params.get('fee_rate', bt.DEFAULTS['fee_rate'])+bt_params.get('slippage_rate', bt.DEFAULTS['slippage_rate']))*100:.2f}%",
        "",
        "---",
        "",
    ]

    printed = []
    need = max(ti.DEFAULTS["ma_windows"]) + ti.DEFAULTS["slope_window"] + 5
    for entry in entries:
        bars, source = ohlcv_data.load_prices(entry, data_cfg)
        tk = entry.get("ticker", "")
        nm = entry.get("company_name", "")
        if len(bars) < need:
            parts.append(f"## {tk} {nm}\nデータ不足でスキップ(source={source})\n\n---\n")
            continue
        res = bt.run_backtest(bars, bench, trend_params, bt_params)
        parts.append(f"## {tk} {nm}")
        parts.append(f"期間: {res['period'][0]} 〜 {res['period'][1]} / 学習・検証の分割日: {res['train_end']}")
        bh = res.get("benchmark_buyhold_full")
        parts.append(f"ベンチマーク同期間バイ&ホールド: {fpct(bh)}")
        parts.append("")
        parts += _fmt_metrics("全期間", res["all"])
        parts.append("")
        parts += _fmt_metrics("学習期間 (in-sample)", res["train"])
        parts.append("")
        parts += _fmt_metrics("検証期間 (out-of-sample)", res["test"])
        parts.append("")
        parts.append("---")
        parts.append("")
        a = res["all"]
        printed.append((tk, a.get("trades", 0), a.get("win_rate"), a.get("total_return")))

    parts.append(f"> {DISCLAIMER}")
    TREND_BACKTEST_REPORT.write_text("\n".join(parts), encoding="utf-8")
    print("バックテストを生成しました:")
    print(f"  - {TREND_BACKTEST_REPORT.relative_to(ROOT)}")
    for tk, n, wr, tr in printed:
        wr_s = f"{wr*100:.0f}%" if wr is not None else "—"
        tr_s = fpct(tr) if tr is not None else "—"
        print(f"    {tk}: 取引{n}回 / 勝率{wr_s} / 累積{tr_s}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Equity Research Radar — 自分用の投資リサーチ・判断ログ")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("trend", help="上昇トレンド分析レポートを生成(メイン)")
    sub.add_parser("backtest-trend", help="トレンド・シグナルの簡易バックテスト")
    sub.add_parser("equity", help="投資リサーチ・判断ログのレポートを生成")
    sub.add_parser("run", help="投資分析ワークフローの概要を出力(補助)")
    args = parser.parse_args()

    if args.command == "trend":
        cmd_trend()
    elif args.command == "backtest-trend":
        cmd_backtest_trend()
    elif args.command == "equity":
        cmd_equity()
    elif args.command == "run":
        cmd_run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
