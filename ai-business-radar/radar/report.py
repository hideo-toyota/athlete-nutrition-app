"""レポート描画(契約: freshness header / uncertainty-first / 断定しない)。"""
from __future__ import annotations

from datetime import date

DISCLAIMER = ("※本レポートは投資助言ではありません。集中度の事実を映すだけで、"
              "売買は指示しません。最終判断と責任は自分にあります。")


def _pct(x):
    return f"{x*100:+.1f}%" if isinstance(x, (int, float)) else "—"


def render_target_check(r: dict, notes=None) -> str:
    i = r["inputs"]

    def pc(x):
        return f"{x*100:.1f}%" if isinstance(x, (int, float)) else "—"

    o = []
    o.append("# Target Check — 10x Feasibility & Ruin Guard")
    o.append("")
    o.append(f"_目標 {i['multiple']:.0f}倍 / {i['years']:.0f}年 / 現資産 {i['initial']:,.0f}円 "
             f"/ 月次積立 {i['monthly']:,.0f}円 / 課税割合 {i['taxable_frac']*100:.0f}%_")
    if notes:
        o.append("")
        for n in notes:
            o.append(f"> {n}")
    o.append("")
    o.append("## まず:これは何か(不確実性)")
    o.append("- これは**目標の難易度とリスクの可視化**。**投資助言でも予測でもなく、銘柄も出しません。**")
    o.append("- リターンは**予測不能**。以下は「仮定の下での算術(CALCULATION)」。指数の歴史値は参考(ASSUMPTION)。")
    o.append("- 数値は**仮定下の点推定を丸めたもの**(±幅のある予測ではない)。桁の精度を確実性と取り違えないこと。")
    o.append("")
    o.append("## 必要リターン [CALCULATION]")
    o.append(f"- 必要CAGR(税前): **{pc(r['cagr_pretax'])}/年**")
    o.append(f"- 税引後 {i['multiple']:.0f}倍に必要な税前倍率: **{r['gross_multiple_posttax']:.2f}倍** "
             f"→ 必要CAGR(税考慮): **{pc(r['cagr_posttax'])}/年**(NISA分は非課税で軽くなる)")
    if r["r_with_contrib"] is None:
        o.append("- 月次積立込みでも、現実的な範囲(〜1000%/年)では到達しない。")
    else:
        o.append(f"- 月次積立込みの必要CAGR: **{pc(r['r_with_contrib'])}/年** "
                 f"(現資産だけなら {pc(r['r_no_contrib'])}/年)。**10xの多くは“貯蓄×時間”で来る**。")
    o.append("")
    o.append("## ★混合の現実(コア/サテライト)[CALCULATION]")
    o.append(f"- **方針配分**(config の目標 コア{i['core_w']*100:.0f}% / サテライト{i['sat_w']*100:.0f}%。"
             "実保有比率ではない)では:")
    for b in r["blend_examples"]:
        o.append(f"  - サテライトが {b['sat_mult']:.0f}倍・{b['core_label']} → **全体 ≈ {b['total_mult']:.2f}倍**")
    if r["core_needed_for_target"] is not None:
        o.append(f"- 全体を {i['multiple']:.0f}倍にするには、サテライト{r['sat_assumed_for_core_calc']:.0f}倍でも "
                 f"**コアが {r['core_needed_for_target']:.1f}倍** 必要(=指数では非現実的)。")
    o.append(f"- → **{i['sat_w']*100:.0f}%枠のサテライトだけでは、原理的に全体{i['multiple']:.0f}xは届かない。**")
    o.append("")
    o.append("## 破綻・回復ライン [WARNING]")
    o.append(f"- サテライト全損時の総資産インパクト: **-{r['sat_max_loss_pct']:.1f}%**")
    o.append("- ドローダウンからの必要回復率: " +
             " / ".join(f"-{d}%→+{v:.0f}%" for d, v in r["recovery"].items()))
    if r["max_dd_recovery"] is not None:
        o.append(f"- 許容DD {i['max_dd_pct']:.0f}% を使い切ると、回復に **+{r['max_dd_recovery']:.0f}%** 必要。")
    if r["leverage_ruin_drop_pct"] is not None:
        o.append(f"- ⚠️ レバレッジ {i['leverage']:.1f}倍 → 約 **-{r['leverage_ruin_drop_pct']:.0f}% の下落で資本毀損(破綻ライン)**。")
    else:
        o.append("- レバレッジ無し(=強制ロスカットによる破綻リスクは低い)。")
    o.append("")
    o.append("## 必要条件(満たさないと到達しない)[INFERENCE]")
    o.append(f"- {pc(r['cagr_posttax'])}/年 を{i['years']:.0f}年継続(税考慮)。分散インデックスの歴史的レンジでは通常困難。")
    o.append("- **規律(上限2.5%/5%/10%)を守れないなら、配分を変えるのではなく目標倍率の方を下げる**のが筋。")
    o.append("- 仮にサテライト比率を上げれば全体は動くが、それは集中とドローダウンを引き受けること(=規律と相反)。")
    o.append("- 不足分は「銘柄選択の超過リターン」より「貯蓄・時間・事業/人的資本」で埋める方が現実的。")
    o.append("")
    o.append("## 破綻条件(これに触れたら危険)[WARNING]")
    o.append("- 生活防衛資金を分離していない / レバレッジで破綻ラインが浅い / 1銘柄・1セクターに上限超で集中。")
    o.append("- 価格下落での狼狽売り、上限を超えるナンピン(=`check` が止める対象)。")
    o.append("")
    o.append("## 規律との両立(所見)[INFERENCE]")
    o.append("- 「余剰資金・現物・分散・上限(2.5%/5%/10%)」を守る範囲では、**純粋な銘柄選択での"
             + f"{i['multiple']:.0f}xは極めて不利**。目標を持つなら、必要年率と破綻幾何を直視した上で、"
             "サイズと撤退を先に決めること。")
    o.append("")
    o.append("> ※これは投資助言ではありません。目標の難易度とリスクを可視化する計算であり、"
             "特定銘柄の推奨・売買指示・利益保証・将来予測ではありません。最終判断は自分にあります。")
    o.append("")
    return "\n".join(o)


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
