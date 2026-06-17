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


VALUE_AUDIT_DISCLAIMER = ("※これは投資助言ではありません。割安“仮説”の検証であり、特定銘柄の推奨・"
                          "売買指示・利益保証・将来予測ではありません。これは購入意思の表明でもありません。"
                          "売買は discipline check + 人間判断が必要です。最終判断は自分にあります。")


def _cond_str(c: dict) -> str:
    """構造化条件を人が読める形に。判定には使わない(表示専用)。"""
    op = c.get("operator", "?")
    th = c.get("threshold")
    tol = c.get("tolerance", 0.0) or 0.0
    metric = c.get("metric", "?")
    if op in ("in_range", "out_of_range") and isinstance(th, (list, tuple)) and len(th) == 2:
        body = f"{op} [{th[0]}, {th[1]}]"
    else:
        body = f"{op} {th}"
    tail = f" (±{tol})" if tol else ""
    return f"`{metric}` {body}{tail}"


def render_value_audit(thesis: dict) -> str:
    """個別 value_audit レポート(4点・不確実性先頭・購入意思でない・免責)。"""
    o = []
    o.append("# Value Audit — 決算 to 決算の割安“仮説”検証")
    o.append("")
    o.append(f"_対象: {thesis.get('ticker')} {thesis.get('company_name') or ''} / "
             f"snapshot: {thesis.get('snapshot_at')} / "
             f"立場: {thesis.get('position_intent', 'paper_only')}_")
    o.append("")
    o.append("> **これは購入意思ではありません(紙上の仮説)。** 売買は `check` → 人間判断 → `log` の系統で。")
    o.append(f"> {VALUE_AUDIT_DISCLAIMER}")
    o.append("")
    # uncertainty-first
    o.append("## まず:これは何か(不確実性)")
    o.append("- これは**割安“仮説”を反証可能な形で固定し、次決算で事後検証する**もの。**銘柄推奨でも予測でもない。**")
    o.append("- 手入力値は **ASSUMPTION**(概算)。そこから計算する指標は CALCULATION(ASSUMPTION依存)。")
    o.append("- 年率10%は**事後測定のハードル(ASSUMPTION)**であり、見込みや保証ではない。")
    o.append("")
    # 1. 検証対象
    o.append("## 1. 検証対象(What we are testing)[INFERENCE]")
    cr = thesis.get("cheapness_reason", {})
    o.append(f"- 安いと考える理由(分類: **{cr.get('classification', '?')}**): {cr.get('explanation', '—')}")
    o.append("- valuation(claim 分類つき・欠損は UNKNOWN で 0 埋めしない):")
    val = thesis.get("valuation", {})
    for k, m in val.items():
        if isinstance(m, dict) and m:
            st = m.get("status", "UNKNOWN")
            vv = m.get("value")
            shown = "UNKNOWN(未取得/欠損)" if (st == "UNKNOWN" or vv is None) else f"{vv}{m.get('unit') or ''}"
            o.append(f"  - {k}: {shown} [{st}]")
        else:
            o.append(f"  - {k}: UNKNOWN(未設定)[UNKNOWN]")
    o.append("")
    # 2. 必要条件
    o.append("## 2. 必要条件(What must hold)[INFERENCE]")
    o.append("- 次決算で以下の事前期待が満たされること(満たさなければ仮説は弱まる):")
    for c in thesis.get("next_earnings_checklist", []):
        if c.get("qualitative_only"):
            o.append(f"  - {c.get('metric', '?')}(定性・一致率の分母外): {c.get('why') or c.get('expectation') or ''}")
        else:
            o.append(f"  - {_cond_str(c)} — {c.get('why') or c.get('expectation') or ''}")
    o.append("")
    # 3. 反証条件
    o.append("## 3. 反証条件(What would break it)[WARNING]")
    o.append("- 次の条件に触れたら仮説は棄却:")
    for c in thesis.get("falsification", []):
        o.append(f"  - {_cond_str(c)} — {c.get('why') or ''}")
    at = thesis.get("anti_thesis", {})
    o.append("- 反対仮説(安さが正当・構造劣化の可能性):")
    o.append(f"  - 安さが正当かも: {at.get('why_cheap_may_be_deserved', '—')}")
    o.append(f"  - 構造劣化かも: {at.get('structural_risk_case', '—')}")
    o.append(f"  - 次決算で強まる条件: {at.get('intensifies_if', '—')}")
    o.append("")
    # 4. 次決算で見る項目
    o.append("## 4. 次決算で見る項目(What to read next)[INFERENCE]")
    for c in thesis.get("next_earnings_checklist", []):
        o.append(f"- `{c.get('metric', '?')}`: {c.get('why') or c.get('expectation') or '仮説の確認点'}")
    for r in thesis.get("key_risks", []):
        o.append(f"- リスク: {r}")
    o.append("")
    o.append(f"> {VALUE_AUDIT_DISCLAIMER}")
    o.append("")
    return "\n".join(o)


def render_value_review(stats: dict, n_active: int) -> str:
    """較正レポート(固定表示順・hit率を先頭に出さない・UNKNOWNを分母に入れない)。"""
    def pct(x):
        return f"{x*100:.0f}%" if isinstance(x, (int, float)) else "—(算出不可/UNKNOWN)"

    o = []
    o.append("# Value Audit Review — 較正(過程 > 結果)")
    o.append("")
    o.append(f"_有効な仮説 {n_active} 件 / 採点済み {stats['n_scored']} 件_")
    o.append("")
    o.append("> **Phase A は手入力仮定(ASSUMPTION)に基づく較正。** 数値は CALCULATION(ASSUMPTION依存)であり"
             "実測 FACT ではない。過信しないこと(原則3)。")
    o.append(f"> {VALUE_AUDIT_DISCLAIMER}")
    o.append("")
    # 1. サンプル不足 / UNKNOWN / 欠損(まず分かっていないこと)
    o.append("## 1. サンプル不足 / UNKNOWN / 欠損(まず読む)")
    if stats["n_scored"] < 20:
        o.append(f"- ⚠️ 採点 {stats['n_scored']} 件 < 20:**統計的な結論は保留**(原則3)。"
                 "決算は年≈4回なので、意味ある較正には数年かかる。")
    o.append(f"- 年率換算が UNKNOWN(サイクル日数が範囲外 等): {stats['n_annualized_unknown']} 件")
    o.append("- 対DCA は **UNKNOWN(未算出)**:Phase A は指数の価格系列が無いため hit率を出さない。")
    o.append("")
    # 2. 反証発火
    o.append("## 2. 反証条件に触れた件数")
    o.append(f"- 反証が発火した採点: **{stats['falsification_outcomes']} 件** "
             f"(発火条件の総数 {stats['falsification_total_triggers']})")
    o.append("")
    # 3. リスク
    o.append("## 3. 規律 / 集中度 / 最大DD")
    if stats["max_dd_known"]:
        o.append(f"- 最大DD(判明分): {', '.join(f'{v:.0f}%' for v in stats['max_dd_known'])}")
    else:
        o.append("- 最大DD: UNKNOWN(日足が無い Phase A では算出しない)。")
    o.append("- 集中度・上限は `mirror` / `check` を併用(本レポートは仮説検証に限定)。")
    o.append("")
    # 4. checklist 一致率
    o.append("## 4. checklist 一致率(構造化フィールドのみ・UNKNOWN除外)")
    o.append(f"- 事前期待と実績の一致率: **{pct(stats['checklist_match_rate'])}** "
             f"(分母 {stats['checklist_den']} 項目)")
    o.append("")
    # 5. 対10%
    o.append("## 5. 対10%ハードル hit率(年率換算が確定したもののみ)")
    o.append(f"- 年率10%換算を超えた割合: **{pct(stats['hit_10pct'])}** "
             f"(分母 {stats['hit_10pct_den']} 件)")
    o.append("")
    # 6. 対DCA
    o.append("## 6. 対DCA hit率")
    if stats["hit_dca_den"]:
        o.append(f"- DCAインデックス超過の割合: **{pct(stats['hit_dca'])}** (分母 {stats['hit_dca_den']} 件)")
    else:
        o.append("- **UNKNOWN(未算出)**:価格系列が無いため Phase A では出さない(負け扱いにもしない)。")
    o.append("")
    o.append(f"> {VALUE_AUDIT_DISCLAIMER}")
    o.append("")
    return "\n".join(o)
