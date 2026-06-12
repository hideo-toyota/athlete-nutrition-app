"""レポート描画(契約: freshness header / uncertainty-first / 断定しない)。"""
from __future__ import annotations

from datetime import date

DISCLAIMER = ("※本レポートは投資助言ではありません。集中度の事実を映すだけで、"
              "売買は指示しません。最終判断と責任は自分にあります。")


def _pct(x):
    return f"{x*100:+.1f}%" if isinstance(x, (int, float)) else "—"


def render_review(rev: dict) -> str:
    o = ["# Journal Review — 較正(過程 > 結果)", ""]
    o.append(f"_判断 {rev['n_decisions']} 件 / 採点済み {rev['n_scored']} 件_")
    o.append("")
    o.append(f"> {DISCLAIMER}")
    o.append("")
    if rev["n_scored"] < 20:
        o.append(f"## ⚠️ サンプル不足({rev['n_scored']}件)— 統計的な結論は出せない(判断保留)")
        o.append("- 数十件・複数の地合いが揃うまで、勝敗は運の範囲。較正は“傾向の芽”として見る(原則3)。")
        o.append("")
    ov = rev["overall"]
    o.append("## 全体")
    o.append(f"- DCAインデックスに勝った割合(hit): {_rate(ov['hit_rate'])}")
    o.append(f"- 平均の対DCA超過: {_pct(ov['avg_excess_vs_dca'])}")
    o.append("")
    o.append("## 裁量 vs 規律(=この道具の検証対象)")
    o.append("| 区分 | 採点数 | hit率 | 平均対DCA超過 |")
    o.append("|---|---|---|---|")
    for label, jp in (("in_discipline", "規律内"), ("override", "規律を破った(override)")):
        a = rev["by_discipline"][label]
        o.append(f"| {jp} | {a['n']} | {_rate(a['hit_rate'])} | {_pct(a['avg_excess_vs_dca'])} |")
    o.append("")
    o.append("> 検証の問い:**あなたの裁量(特にoverride)は、DCAに勝てているか?** "
             "勝てていないと出たら、それは失敗でなく『黙ってDCA』という最も価値ある真実(原則5)。")
    o.append("")
    o.append(f"> {DISCLAIMER}")
    o.append("")
    return "\n".join(o)


def _rate(x):
    return f"{x*100:.0f}%" if isinstance(x, (int, float)) else "—"


def render_check(verdict: dict) -> str:
    act = verdict["action"]
    head = "✅ 規律OK" if verdict["ok"] else "⛔ 規律により却下"
    o = []
    o.append("# Discipline Check — 規律の番人")
    o.append("")
    amt = act.get("amount")
    o.append(f"_提案: **{act['verb']} {act.get('ticker') or ''}**"
             + (f" {amt:,.0f}円" if amt else "")
             + f" / セクター: {verdict['sector_used']}_")
    o.append("")
    o.append(f"## 判定: **{head}**")
    o.append("")
    if verdict["breaches"]:
        o.append("### ⛔ 却下理由(ハード)")
        o += [f"- {b}" for b in verdict["breaches"]]
        o.append("")
    if verdict["warnings"]:
        o.append("### ⚠️ 警告(失敗モード)")
        o += [f"- {w}" for w in verdict["warnings"]]
        o.append("")
    if verdict["notes"]:
        o.append("### 📝 メモ")
        o += [f"- {n}" for n in verdict["notes"]]
        o.append("")
    o.append("> これは規律チェック。**買え/売れの指示ではない。** 最終判断と、規律を破る場合の理由記録はあなたの仕事(原則1・2)。")
    o.append("")
    o.append(f"> {DISCLAIMER}")
    o.append("")
    return "\n".join(o)


def _table(col: str, d: dict, top: int | None = None) -> str:
    items = sorted(d.items(), key=lambda kv: kv[1], reverse=True)
    if top:
        items = items[:top]
    lines = [f"| {col} | % |", "|---|---|"]
    for k, v in items:
        lines.append(f"| {k} | {v:.1f}% |")
    return "\n".join(lines)


def render_mirror(exp: dict, portfolio: dict, cfg: dict, asof: str | None = None) -> str:
    as_of = portfolio.get("as_of", "?")
    staleness_days = cfg.get("policy", {}).get("discipline", {}).get("staleness_days", 5)
    ref = date.fromisoformat(asof) if asof else date.today()
    try:
        age = (ref - date.fromisoformat(as_of)).days
    except ValueError:
        age = None
    stale = age is not None and age > staleness_days
    if age is None:
        age_str = "不明"
    elif age <= 0:
        age_str = "本日基準"
    else:
        age_str = f"{age}日前"

    lt = exp["lookthrough"]
    sat = exp["satellite"]
    caps = sat["caps"]
    cur = cfg.get("measure_currency", "JPY")

    o = []
    o.append("# Honest Mirror — 正直な集中度レポート")
    o.append("")
    o.append(f"_基準日(as_of): {as_of} / データ鮮度: {age_str}"
             + (" ⚠️**古い可能性**" if stale else "")
             + f" / 測定通貨: {cur} / 総額: {exp['total_jpy']:,.0f}円_")
    o.append("")
    o.append(f"> {DISCLAIMER}")
    o.append("")
    # uncertainty-first(原則3)
    o.append("## まず:分かっていないこと(不確実)")
    if exp.get("index_meta"):
        o.append("- 指数の構成は **手入力の概算**(`indices/*.json`)。look-through は概算値。")
    o.append("- 時価・為替は基準日時点の手入力。リアルタイムではない。")
    for m in exp.get("index_meta", []):
        o.append(f"- 指数 `{m['ref']}`: 構成as_of {m.get('as_of') or '不明'} / "
                 f"ウェイト合計 セクター{m['sector_sum']:.2f}・地域{m['region_sum']:.2f}・通貨{m['currency_sum']:.2f} / "
                 f"上位銘柄カバー {m['top_sum']*100:.0f}%(残りは『その他』)")
    for w in exp.get("data_warnings", []):
        o.append(f"- ⚠️ {w}")
    o.append("")
    # honest mirror headline
    sec = lt["by_sector"]
    curex = lt["by_currency"]
    o.append("## 正直な鏡(look-through = 指数の中身まで合算)")
    o.append("_以下は CALCULATION(指数構成は手入力概算=ASSUMPTION依存)。精密値ではなく目安。_")
    o.append(f"- **実質 US-Tech/AI に ≈{sec.get('US-Tech/AI', 0):.0f}%**(概算)賭けている。")
    o.append(f"- **USD建てエクスポージャー ≈{curex.get('USD', 0):.0f}%**(概算/=隠れた円高・円安の賭け)。")
    nvda = lt["by_name"].get("NVDA")
    if nvda is not None:
        o.append(f"- 例:NVDA は直接保有+指数経由の合算で **{nvda:.1f}%**(直接だけ見ると過小評価)。")
    o.append("")
    o.append(_table("セクター(look-through)", sec))
    o.append("")
    o.append(_table("通貨(look-through)", curex))
    o.append("")
    o.append(_table("地域(look-through)", lt["by_region"]))
    o.append("")
    o.append(_table("銘柄 上位(look-through)", lt["by_name"], top=8))
    o.append("")
    # satellite discipline
    o.append("## サテライト(個別株)規律チェック")
    o.append(f"- 個別株 合計: **{sat['individual_pct']:.1f}%** / 上限 {caps['max_pct_of_total']}% "
             + ("→ ⚠️**超過**" if sat["over_total_cap"] else "→ ✅ OK"))
    o.append(f"- 銘柄数: {sat['n_names']} / 推奨 {caps.get('min_names')}〜{caps.get('max_names')}"
             + ("  → ⚠️**少なすぎ(分散不足)**" if sat["under_min_names"] else ""))
    for tk, p in sorted(sat["name_breaches"].items(), key=lambda x: -x[1]):
        o.append(f"  - ⚠️ {tk}: {p:.1f}%  > 1銘柄上限 {caps['max_pct_per_name']}%")
    for s, p in sorted(sat["sector_breaches"].items(), key=lambda x: -x[1]):
        o.append(f"  - ⚠️ セクター {s}: {p:.1f}%  > セクター上限 {caps['max_pct_per_sector']}%")
    if not sat["name_breaches"] and not sat["sector_breaches"] and not sat["over_total_cap"]:
        o.append("- ✅ サテライトの上限はすべて範囲内。")
    o.append("")
    o.append("> 判断ラベルは出さない。これは“鏡”であって指示ではない。次の一手は `check` で規律に通すこと。")
    o.append("")
    o.append(f"> {DISCLAIMER}")
    o.append("")
    return "\n".join(o)
