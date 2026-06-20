"""CLI(MVP: mirror)。実行: `python3 -m radar mirror`(ai-business-radar/ で)。"""
from __future__ import annotations

import argparse
import csv as csv_module
import json
import re
from datetime import date
from pathlib import Path

from .concentration import look_through
from .config import load_config
from .data import load_portfolio
from .discipline import check
from . import journal
from . import target_check
from . import value_audit
from . import value_store
from .features import (
    build_edinet_company_map,
    build_financial_features,
    build_financial_features_batch,
    build_jquants_bulk_features,
)
from .research import (build_audit_report, build_evidence, build_jquants_evidence,
                       build_llm_handoff, build_research_queue, write_audit_report,
                       write_evidence, write_jquants_evidence, write_llm_handoff,
                       write_research_queue)
from .daily_update import render_daily_summary, run_daily_update
from .sources import edinet_db
from .report import (render_check, render_mirror, render_review, render_target_check,
                     render_value_audit, render_value_review)

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"


def _valid_asof(asof: str | None) -> str | None:
    if asof is None:
        return None
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError:
        raise SystemExit(f"--asof が実在しない日付です: {asof}")
    return asof


def cmd_mirror(asof: str | None = None) -> None:
    asof = _valid_asof(asof)
    cfg = load_config()
    pf = load_portfolio()
    exp = look_through(pf, cfg)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "honest_mirror.md"
    out.write_text(render_mirror(exp, pf, cfg, asof=asof), encoding="utf-8")
    # CSV(SPEC契約: md + csv)
    lt = exp["lookthrough"]
    csv_path = OUTPUTS / "honest_mirror.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        wr = csv_module.writer(f)
        wr.writerow(["dimension", "key", "pct"])
        for dim in ("by_sector", "by_region", "by_currency", "by_name"):
            for k, v in sorted(lt[dim].items(), key=lambda kv: kv[1], reverse=True):
                wr.writerow([dim, k, round(v, 2)])
    print(f"honest mirror を生成しました: {out.relative_to(ROOT)} / {csv_path.relative_to(ROOT)}")
    print(f"  実質 US-Tech/AI: {lt['by_sector'].get('US-Tech/AI', 0):.0f}%"
          f" / USD: {lt['by_currency'].get('USD', 0):.0f}%"
          f" / 個別株: {exp['satellite']['individual_pct']:.1f}%"
          + ("  ⚠️上限超過あり" if (exp['satellite']['over_total_cap']
             or exp['satellite']['name_breaches']
             or exp['satellite']['sector_breaches']) else ""))


def cmd_check(action_tokens: list[str]) -> None:
    cfg = load_config()
    pf = load_portfolio()
    verdict = check(pf, cfg, " ".join(action_tokens))
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "discipline_check.md"
    out.write_text(render_check(verdict), encoding="utf-8")
    head = "✅ OK" if verdict["ok"] else "⛔ 却下"
    print(f"discipline check: {head}  (→ {out.relative_to(ROOT)})")
    for b in verdict["breaches"]:
        print(f"  ⛔ {b}")
    for w in verdict["warnings"]:
        print(f"  ⚠️ {w}")


def _load_json(p: Path, what: str) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{what} の JSON が不正です({p}): {e}")


def cmd_log(path: str | None) -> None:
    p = Path(path) if path else (ROOT / "journal" / "decision_input.json")
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        raise SystemExit(f"判断入力が見つかりません: {p}(journal/decision_input.example.json を参照)")
    entry = _load_json(p, "判断入力")
    did = journal.append_decision(entry)
    print(f"判断を記録しました id={did} → {journal.LOG.relative_to(ROOT)}(追記専用)")


def cmd_score(path: str | None, asof: str | None = None) -> None:
    p = Path(path) if path else (ROOT / "journal" / "prices.json")
    if not p.is_absolute():
        p = ROOT / p
    prices = _load_json(p, "価格") if p.exists() else {}
    res = journal.score_due(prices, asof=_valid_asof(asof))
    print(f"採点: 新規 {len(res['scored'])} 件 / 期日前 {len(res['pending_future'])} 件 / "
          f"価格待ち {len(res['awaiting_price'])} 件")
    if res["awaiting_price"]:
        print(f"  価格待ち id: {res['awaiting_price']}(journal/prices.json に horizon の終値を)")


def cmd_review() -> None:
    rev = journal.review()
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "journal_review.md"
    out.write_text(render_review(rev), encoding="utf-8")
    ov = rev["overall"]
    hr = f"{ov['hit_rate']*100:.0f}%" if isinstance(ov["hit_rate"], (int, float)) else "—"
    print(f"較正: 判断{rev['n_decisions']}件 / 採点{rev['n_scored']}件 / 対DCA hit {hr} → {out.relative_to(ROOT)}")
    if rev["n_scored"] < 20:
        print("  ⚠️ サンプル不足:統計的な結論は保留(原則3)")


def _portfolio_defaults() -> tuple[float, float]:
    """portfolio.json から (現資産総額, 課税割合) を導出。account に 'nisa' を含む保有は非課税、
    それ以外(account 未指定を含む)は課税扱い(=保守的)。値は表示しない・銘柄も扱わない。"""
    pf = load_portfolio()
    holdings = pf.get("holdings", [])
    if not isinstance(holdings, list):
        raise SystemExit("portfolio.holdings はリストである必要があります")
    total = 0.0
    taxable = 0.0
    for h in holdings:
        mv = h.get("market_value_jpy", 0)
        if isinstance(mv, bool) or not isinstance(mv, (int, float)):
            raise SystemExit("portfolio: market_value_jpy は数値である必要があります")
        if mv < 0:
            raise SystemExit("portfolio: market_value_jpy は非負である必要があります")
        total += mv
        account = str(h.get("account", "")).lower()
        if "nisa" not in account:
            taxable += mv
    if total <= 0:
        raise SystemExit("portfolio の市場価値合計が 0 です(--initial を明示してください)")
    return total, taxable / total


def _config_blend() -> tuple[float, float, float]:
    """config.json から (core_w, sat_w, sat_cap_pct) を導出。"""
    cfg = load_config()
    cs = cfg["policy"].get("core_satellite", {})
    core_pct = cs.get("core_pct", 90)
    sat_pct = cs.get("satellite_pct", 10)
    import math
    for k, v in (("core_pct", core_pct), ("satellite_pct", sat_pct)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            raise SystemExit(f"config: core_satellite.{k} が不正(有限・非負の数値)")
    s = core_pct + sat_pct
    if s <= 0:
        raise SystemExit("config: core_satellite の合計が 0 です")
    sat_cap = cfg["policy"].get("satellite", {}).get("max_pct_of_total", 10)
    return core_pct / s, sat_pct / s, float(sat_cap)


def cmd_target_check(args) -> None:
    """B4: 目標倍率の必要条件/破綻条件を純計算で可視化。ネット無し・銘柄無し・推奨無し・予測無し。"""
    _valid_asof(args.asof)  # 形式検証のみ(再現可能性のため受け付ける)
    notes = []
    if args.initial is not None:
        initial = args.initial
        taxable_frac = args.taxable_frac if args.taxable_frac is not None else 1.0
        if args.taxable_frac is None:
            notes.append("課税割合は --taxable-frac 未指定のため 100%(全課税)を仮定。")
    else:
        initial, derived_taxable = _portfolio_defaults()
        if args.taxable_frac is not None:
            taxable_frac = args.taxable_frac
        else:
            taxable_frac = derived_taxable
            notes.append("課税割合は portfolio.json から導出(account に 'nisa' を含む保有を非課税、"
                         "account 未指定を含むそれ以外は課税扱い=保守的)。正確には口座区分を明示のこと。")
    core_w, sat_w, sat_cap_pct = _config_blend()
    notes.append("コア/サテライト比は config.json の**方針目標**であり、実保有比率ではない。")

    r = target_check.compute(
        args.multiple, args.years,
        initial=initial, monthly=args.monthly,
        taxable_frac=taxable_frac, tax_rate=args.tax_rate,
        core_w=core_w, sat_w=sat_w, sat_cap_pct=sat_cap_pct,
        leverage=args.leverage, max_dd_pct=args.max_dd,
    )
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "target_check.md"
    out.write_text(render_target_check(r, notes=notes), encoding="utf-8")
    print(f"target check を生成しました: {out.relative_to(ROOT)}")
    print(f"  目標 {args.multiple:.0f}倍 / {args.years:.0f}年 → 必要CAGR(税前) {r['cagr_pretax']*100:.1f}%/年"
          f" / 税考慮 {r['cagr_posttax']*100:.1f}%/年")
    print(f"  ★{sat_w*100:.0f}%枠サテライトのみでは全体{args.multiple:.0f}xは原理的に不可"
          "(必要条件/破綻条件は出力を参照)。これは予測でも助言でもありません。")


def _va_config() -> dict:
    """config.json の value_audit ブロック(既定値で補完)。"""
    cfg = load_config()
    d = dict(cfg.get("value_audit") or {})
    d.setdefault("annual_hurdle_pct", 10)
    d.setdefault("annualization_day_base", 365)
    d.setdefault("min_cycle_days", 45)
    d.setdefault("max_cycle_days", 200)
    return d


def _resolve_path(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (ROOT / q)


def _rel(p: Path):
    try:
        return p.relative_to(ROOT)
    except ValueError:
        return p


def _load_edinet_codes_file(path: str) -> list[str]:
    """data/metadata 配下の EDINET code list を読む。値はエラーに含めない。"""
    p = _resolve_path(path).resolve()
    allowed_root = (ROOT / "data" / "metadata").resolve()
    if allowed_root != p.parent and allowed_root not in p.parents:
        raise SystemExit("--codes-file は data/metadata 配下のコード一覧に限定しています")
    if not p.exists() or not p.is_file():
        raise SystemExit("--codes-file が見つかりません")
    codes = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as e:
        raise SystemExit("--codes-file は UTF-8 テキストで指定してください") from e
    for lineno, line in enumerate(lines, start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        token = s.split(",", 1)[0].strip()
        if not codes and token.lower() in {"edinet_code", "code"}:
            continue
        try:
            codes.append(edinet_db._valid_edinet_code(token))
        except SystemExit as e:
            raise SystemExit(f"--codes-file の {lineno} 行目が EDINETコード(E02367形式)ではありません") from e
    if not codes:
        raise SystemExit("--codes-file に EDINETコードがありません")
    return codes


def _sync_batch_limit(cfg: dict, explicit_limit: int | None) -> int:
    if explicit_limit is not None:
        return explicit_limit
    budget = (cfg.get("data_layer") or {}).get("daily_request_budget")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        return edinet_db.DEFAULT_BATCH_LIMIT
    return min(edinet_db.DEFAULT_BATCH_LIMIT, budget)


def cmd_value_audit_register(args) -> None:
    """B5: 割安“仮説”を事前固定(紙上・購入意思ではない)。手入力 snapshot のみ・ネット無し。"""
    if not args.from_file:
        raise SystemExit("Phase A は手入力です: value-audit register <ticker> --from-file <json>")
    asof_d = value_store.valid_asof(args.asof) or date.today()
    d = value_store.load_thesis_input(_resolve_path(args.from_file))
    if args.ticker and d.get("ticker") != args.ticker:
        raise SystemExit(f"--from-file の ticker({d.get('ticker')})と引数 ticker({args.ticker})が一致しません")
    # PIT: snapshot / cycle 起点 / 各 valuation の available_at <= asof(未来混入を拒否)
    if value_store.parse_dt_date(d["snapshot_at"], "snapshot_at") > asof_d:
        raise SystemExit(f"snapshot_at が asof より未来です(PIT 違反): {d['snapshot_at']} > {asof_d}")
    if value_store.parse_dt_date(d["cycle"]["start_available_at"], "cycle.start_available_at") > asof_d:
        raise SystemExit(f"cycle.start_available_at が asof より未来です(PIT 違反): > {asof_d}")
    for k, m in (d.get("valuation") or {}).items():
        if isinstance(m, dict) and m.get("available_at"):
            if value_store.parse_dt_date(m["available_at"], f"valuation.{k}.available_at") > asof_d:
                raise SystemExit(f"valuation.{k}.available_at が asof より未来です(PIT 違反)")
    # min_metrics_for_audit: 使える metric が少なければ「評価不能」を出力に明示(拒否はしない)
    va_cfg = _va_config()
    min_metrics = cfg_min = va_cfg.get("min_metrics_for_audit", 3)
    usable = sum(1 for m in (d.get("valuation") or {}).values()
                 if isinstance(m, dict) and m.get("status") in ("FACT", "CALCULATION", "ASSUMPTION")
                 and value_audit._finite(m.get("value")))
    eval_warning = None
    if usable < min_metrics:
        eval_warning = (f"評価不能/UNKNOWN多すぎ:有効な valuation 指標は {usable} 件で "
                        f"min_metrics_for_audit={cfg_min} 未満。割安判断の土台が薄いことを直視のこと。")
    thesis_id = value_store.append_thesis(d, asof=asof_d.isoformat())
    slug = value_store.validate_ticker(d["ticker"])
    out = value_store.safe_output_path(slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_value_audit(d, eval_warning=eval_warning), encoding="utf-8")
    print(f"value-audit 仮説を登録しました(紙上・購入意思ではない): thesis_id={thesis_id}")
    print(f"  → {_rel(out)} / {_rel(value_store.THESIS_LOG)}(追記専用)")
    print("  ※ これは買い候補でも推奨でも予測でもありません。売買は check → 人間 → log。")


def cmd_value_audit_score(args) -> None:
    """B5: 次決算後の手入力実績で事後採点(対DCA=UNKNOWN・凍結・冪等)。ネット無し。"""
    if not args.from_file:
        raise SystemExit("Phase A は手入力です: value-audit score --from-file <json>")
    oin = value_store.load_outcome_input(_resolve_path(args.from_file))
    asof_str = args.asof or oin.get("asof")
    asof_d = value_store.valid_asof(asof_str)
    if asof_d is None:
        raise SystemExit("asof が必要です(--asof か入力の asof)")
    va_cfg = _va_config()

    all_theses = value_store.read_theses()
    if not any(t.get("thesis_id") == oin["thesis_id"] for t in all_theses):
        raise SystemExit(f"thesis_id が見つかりません: {oin['thesis_id']}(先に register)")
    actives = {t["thesis_id"]: t for t in value_store.active_theses()}
    th = actives.get(oin["thesis_id"])
    if th is None:
        print(f"thesis_id={oin['thesis_id']} は superseded(無効版)のため採点をスキップします(既存 outcome は不変)。")
        return

    nea = oin["next_earnings_available_at"]
    if value_store.parse_dt_date(nea, "next_earnings_available_at") > asof_d:
        print(f"次決算 available_at={nea} は asof={asof_d} より未来 → pending(採点しない)。")
        return

    start_at = th["cycle"]["start_available_at"]
    start_d = value_store.parse_dt_date(start_at, "cycle.start_available_at")
    end_d = value_store.parse_dt_date(nea, "next_earnings_available_at")
    days = value_audit.cycle_days(start_d.toordinal(), end_d.toordinal())

    # 価格 PIT / 後知恵防止: 価格の available_at を asof・サイクル境界と突合
    entry_av = value_store.parse_dt_date(oin["entry_price_available_at"], "entry_price_available_at")
    exit_av = value_store.parse_dt_date(oin["exit_price_available_at"], "exit_price_available_at")
    if entry_av > asof_d or exit_av > asof_d:
        raise SystemExit(f"価格の available_at が asof({asof_d})より未来です(PIT 違反・後知恵)")
    if entry_av < start_d:
        raise SystemExit("entry_price_available_at は cycle.start_available_at 以降である必要があります")
    if exit_av < end_d:
        raise SystemExit("exit_price_available_at は next_earnings_available_at 以降である必要があります")

    raw = value_audit.raw_return(oin["entry_price"], oin["exit_price"])
    raw_m = value_audit.measured(raw, value_audit.CALCULATION, unit="%", note="ASSUMPTION依存(手入力価格)")
    ann = value_audit.annualize(raw, days, va_cfg)
    if ann.get("status") == value_audit.CALCULATION:
        ann["note"] = "ASSUMPTION依存(手入力価格)"
    hurdle = va_cfg["annual_hurdle_pct"] / 100.0
    vs10 = value_audit.vs_target(ann, hurdle)

    actuals = oin["actuals"]

    def _actual_measured(metric):
        v = actuals.get(metric)
        if value_audit._finite(v):
            return value_audit.measured(float(v), value_audit.ASSUMPTION)
        return value_audit.unknown(note="手入力 actual 欠損")

    checklist_result = []
    for c in th.get("next_earnings_checklist", []):
        if c.get("qualitative_only"):
            checklist_result.append({"metric": c.get("metric"), "qualitative_only": True,
                                     "actual": value_audit.unknown(), "matched": None})
            continue
        am = _actual_measured(c["metric"])
        try:
            matched = value_audit.evaluate_condition(c, am)
        except ValueError as e:
            raise SystemExit(f"checklist 判定エラー({c.get('metric')}): {e}")
        checklist_result.append({"metric": c["metric"], "operator": c["operator"],
                                 "threshold": c["threshold"], "tolerance": c.get("tolerance", 0.0),
                                 "actual": am, "matched": matched,
                                 "qualitative_only": False, "judge_basis": "構造化比較(operator真理表)"})

    fired = []
    for c in th.get("falsification", []):
        am = _actual_measured(c["metric"])
        try:
            res = value_audit.evaluate_condition(c, am)
        except ValueError as e:
            raise SystemExit(f"falsification 判定エラー({c.get('metric')}): {e}")
        if res is True:
            fired.append({"metric": c["metric"], "operator": c["operator"],
                          "threshold": c["threshold"], "actual": am})

    outcome = {
        "thesis_id": oin["thesis_id"], "scored_at": asof_d.isoformat(), "asof": asof_d.isoformat(),
        "source": "manual", "cycle_start_available_at": start_at, "next_earnings_available_at": nea,
        "price_basis": oin["price_basis"],
        "entry_price_date": oin["entry_price_date"], "entry_price_available_at": oin["entry_price_available_at"],
        "exit_price_date": oin["exit_price_date"], "exit_price_available_at": oin["exit_price_available_at"],
        "cycle_days": days, "raw_return": raw_m, "annualized_return": ann, "vs_target_10pct": vs10,
        "benchmark": {"method": "dca_index", "index_ref": va_cfg.get("benchmark_index_ref"),
                      "return": value_audit.unknown(note="no_price_series(Phase A)")},
        "excess_vs_dca": value_audit.unknown(note="no_price_series(Phase A)"),
        "beat_dca": value_audit.unknown(note="no_price_series(Phase A)"),
        "max_drawdown_pct": value_audit.unknown(note="日足無し(Phase A)"),
        "checklist_result": checklist_result, "falsification_triggered": fired,
        "cheapness_resolution": "undetermined",
        "claim_tags": {"actuals": "ASSUMPTION", "computed": "CALCULATION(ASSUMPTION依存)"},
    }
    if oin.get("amends"):
        outcome["amends"] = oin["amends"]
    event_id, written = value_store.append_outcome(outcome)
    if not written:
        print(f"already_scored: 同一キーの採点が既にあります(追記しません)。thesis_id={oin['thesis_id']}")
        return
    ann_txt = f"{ann['value']*100:.1f}%/年" if ann.get("status") == value_audit.CALCULATION else "UNKNOWN(範囲外)"
    print(f"採点しました(手入力仮定・対DCA=UNKNOWN): outcome_id={event_id}")
    print(f"  raw {raw*100:.1f}% / {days}日 → 年率 {ann_txt} / 反証発火 {len(fired)} 件")
    print("  ※ これは予測でも推奨でもありません。手入力前提(ASSUMPTION)の事後測定です。")


def cmd_value_audit_review(args) -> None:
    """B5: 較正(固定表示順・hit率を先頭に出さない・対DCA=UNKNOWN)。ネット無し。"""
    value_store.valid_asof(args.asof)
    va_cfg = _va_config()
    outcomes = value_store.read_outcomes()
    actives = value_store.active_theses()
    n_active = len(actives)
    stats = value_audit.aggregate(outcomes, va_cfg)
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / "value_audit_review.md"
    out.write_text(render_value_review(stats, n_active, active_theses=actives), encoding="utf-8")
    print(f"value-audit 較正: 有効仮説 {n_active} 件 / 採点 {stats['n_scored']} 件 → {_rel(out)}")
    if stats["n_scored"] < 20:
        print("  ⚠️ サンプル不足:統計的な結論は保留(原則3)。対DCA は Phase A では UNKNOWN(未算出)。")


def cmd_value_audit(args) -> None:
    if args.va_command == "register":
        cmd_value_audit_register(args)
    elif args.va_command == "score":
        cmd_value_audit_score(args)
    elif args.va_command == "review":
        cmd_value_audit_review(args)
    else:
        raise SystemExit("使い方: value-audit {register|score|review} ...")


def cmd_data_check(offline: bool, live: bool = False, provider: str | None = None) -> None:
    """A0(--offline): ネット無しのキー存在/redact 確認。A1(--live): 軽量疎通のみ。

    **キー値も response 本文も表示しない・保存しない・LLM に渡さない。** --live が無ければ外部接続しない。
    A1 は「疎通のみ」(ToS)。sync/raw保存/第三者LLM入力は未実装・NO-GO のまま。
    """
    import os
    from .sources import common
    if offline and live:
        raise SystemExit("--offline と --live は同時指定できません")
    if provider and not live:
        raise SystemExit("--provider は --live 専用です")
    if live:
        from .sources import live as live_mod
        if not provider:
            raise SystemExit(f"--live には --provider が必要です(choices: {live_mod.PROVIDERS})")
        cfg = load_config()
        res = live_mod.ping(provider, cfg)   # 本文は保存も表示もしない
        head = "✅ 疎通OK" if res["success"] else "⛔ 疎通NG"
        print(f"data-check --live [{res['provider']}]: {head}")
        print(f"  endpoint: {res['endpoint']} / HTTP status: {res['status']} / 試行 {res['attempts']}")
        if res["error"]:
            print(f"  error(redact済): {res['error']}")
        print("  ※ 疎通可否のみ。取得本文は保存も表示もせず、Claude にも渡していません(A1)。")
        print("  ※ sync(raw保存)・第三者LLM入力は未実装・ToS確認まで NO-GO。")
        return
    if not offline:
        raise SystemExit("外部接続するには `data-check --live --provider <jquants|edinet-db>`。"
                         "ネット無し確認は `data-check --offline`。")
    common._load_dotenv()
    for name in common.KEY_VARS:
        print(f"  {name}: {'設定あり' if os.environ.get(name) else '未設定'}")  # ★値は出さない
    sample = "Authorization: Bearer DUMMY.TOKEN.VALUE"
    print(f"  redact動作: {common.redact(sample)}")
    print("  ※ 外部APIには接続していません(A0)。実疎通は `--live` で。")


def cmd_sync(args) -> None:
    """Phase B minimum sync. Scope is EDINET DB companies/financials only."""
    asof = _valid_asof(args.asof) or date.today().isoformat()
    if args.provider != edinet_db.PROVIDER:
        raise SystemExit("Phase B の最小 sync は --provider edinet-db のみ対応")
    cfg = load_config()
    code = getattr(args, "code", None)
    codes_file = getattr(args, "codes_file", None)
    offset = getattr(args, "offset", 0)
    limit_arg = getattr(args, "limit", None)
    if args.dataset == edinet_db.DATASET:
        if code or codes_file:
            raise SystemExit("--dataset companies では --code は使いません")
        if offset != 0 or limit_arg is not None:
            raise SystemExit("--dataset companies では --offset/--limit は使いません")
        if args.years != edinet_db.DEFAULT_YEARS or args.period != "annual":
            raise SystemExit("--dataset companies では --years/--period は使いません")
        res = edinet_db.sync_companies(
            cfg,
            asof=asof,
            page=args.page,
            per_page=args.per_page,
        )
        print(f"sync [{res['provider']}:{res['dataset']}]: raw+provenance を保存しました")
        print(f"  raw: {_rel(res['raw_path'])}")
        print(f"  provenance: {_rel(res['provenance_path'])}")
        print(f"  fetch_log: data/metadata/fetch_log.jsonl")
        print(f"  asof: {res['asof']} / available_at: {res['available_at']} / 試行 {res['attempts']}")
    elif args.dataset == edinet_db.DATASET_FINANCIALS:
        if bool(code) == bool(codes_file):
            raise SystemExit("--dataset financials では --code か --codes-file のどちらか一方が必須です")
        if args.page != edinet_db.DEFAULT_PAGE or args.per_page != edinet_db.DEFAULT_PER_PAGE:
            raise SystemExit("--dataset financials では --page/--per-page は使いません")
        if codes_file:
            codes = _load_edinet_codes_file(codes_file)
            limit = _sync_batch_limit(cfg, limit_arg)
            res = edinet_db.sync_financials_batch(
                cfg,
                asof=asof,
                codes=codes,
                offset=offset,
                limit=limit,
                years=args.years,
                period=args.period,
            )
            print(f"sync [{res['provider']}:{res['dataset']}:batch]: raw+provenance を保存/確認しました")
            print(f"  manifest: {_rel(res['manifest_path'])}")
            print(f"  selected: {res['selected_count']} / saved: {res['saved_count']}"
                  f" / skipped_existing: {res['skipped_existing_count']} / failures: {res['failure_count']}")
            print(f"  offset: {res['offset']} → next_offset: {res['next_offset']}"
                  f" / end_offset: {res['end_offset']} / 試行 {res['total_attempts']}"
                  f" / asof既使用 {res['prior_attempts_for_asof']}")
            print("  ※ 取得本文・APIキー値は表示していません。feature/research_queue/evidence/LLM投入はしていません。")
            if res["failure_count"]:
                raise SystemExit(f"financials batch に失敗があります(--offset {res['retry_offset']} から再開してください)")
            return
        if offset != 0 or limit_arg is not None:
            raise SystemExit("--code 単体指定では --offset/--limit は使いません")
        res = edinet_db.sync_financials(cfg, asof=asof, code=code, years=args.years, period=args.period)
        print(f"sync [{res['provider']}:{res['dataset']}]: raw+provenance を保存しました")
        print(f"  raw: {_rel(res['raw_path'])}")
        print(f"  provenance: {_rel(res['provenance_path'])}")
        print(f"  fetch_log: data/metadata/fetch_log.jsonl")
        print(f"  asof: {res['asof']} / available_at: {res['available_at']} / 試行 {res['attempts']}")
    else:
        raise SystemExit("Phase B の最小 sync は companies|financials のみ対応")
    print("  ※ 取得本文・APIキー値は表示していません。feature/research_queue/evidence/LLM投入は未実装です。")


def cmd_build_features(args) -> None:
    """Phase C minimal feature build. Reads existing raw only; no network/env/API key."""
    asof = _valid_asof(args.asof) or date.today().isoformat()
    if args.provider != "edinet-db" or args.dataset != "financials":
        raise SystemExit("Phase C minimal build-features は --provider edinet-db --dataset financials のみ対応")
    if bool(args.raw_path) == bool(args.raw_dir):
        raise SystemExit("--raw-path か --raw-dir のどちらか一方が必要です")
    if args.raw_dir:
        res = build_financial_features_batch(raw_dir=args.raw_dir, asof=asof, limit=args.limit)
        print(f"build-features [{res['provider']}:{res['dataset']}:batch]: derived を生成しました")
        print(f"  manifest: {_rel(res['manifest_path'])}")
        print(f"  raw_dir: {_rel(res['raw_dir'])}")
        print(f"  candidates: {res['candidate_count']} / built: {res['built_count']}"
              f" / skipped_missing_provenance: {res['skipped_missing_provenance_count']}"
              f" / failures: {res['failure_count']}")
        print("  ※ raw本文・APIキー値は表示していません。ランキング/推奨/予測は生成していません。")
        if res["failure_count"]:
            raise SystemExit("build-features batch に失敗があります(manifest を確認してください)")
        return
    res = build_financial_features(raw_path=args.raw_path, asof=asof)
    print(f"build-features [{res['provider']}:{res['dataset']}]: derived を生成しました")
    print(f"  output: {_rel(res['output_path'])}")
    print(f"  feature_set: {res['feature_set']} / asof: {res['asof']} / edinet_code: {res['edinet_code']}")
    print(f"  features: {res['feature_count']} / UNKNOWN: {res['unknown_count']}")
    print(f"  input_hash: {res['raw_hash_normalized']}")
    print("  ※ raw本文・APIキー値は表示していません。research_queue/evidence/LLM投入は未実装です。")


def cmd_build_jquants_features(args) -> None:
    """Build local J-Quants bulk features. Reads existing raw only; no network/env/API key."""
    asof = _valid_asof(args.asof)
    if asof is None:
        raise SystemExit("--asof が必要です")
    res = build_jquants_bulk_features(asof=asof)
    print(f"build-jquants-features [{res['provider']}:{res['dataset']}]: derived を生成しました")
    print(f"  features: {_rel(res['features_path'])}")
    print(f"  summary: {_rel(res['summary_path'])}")
    print(f"  manifest: {_rel(res['manifest_path'])}")
    print(f"  rows: {res['feature_rows']} / input_files: {res['input_file_count']}")
    print(f"  price_coverage: {res['coverage']['price_coverage_ratio']*100:.1f}%"
          if isinstance(res['coverage'].get('price_coverage_ratio'), (int, float)) else "  price_coverage: UNKNOWN")
    print(f"  valuation_coverage: {res['coverage']['valuation_coverage_ratio']*100:.1f}%"
          if isinstance(res['coverage'].get('valuation_coverage_ratio'), (int, float))
          else "  valuation_coverage: UNKNOWN")
    print("  ※ raw本文・APIキー値は表示していません。ランキング/推奨/予測は生成していません。")


def cmd_build_company_map(args) -> None:
    """Build EDINET code -> securities code derived map. Reads companies raw only."""
    asof = _valid_asof(args.asof)
    if asof is None:
        raise SystemExit("--asof が必要です")
    res = build_edinet_company_map(raw_dir=args.raw_dir, asof=asof)
    print(f"build-company-map [{res['provider']}:{res['dataset']}]: derived map を生成しました")
    print(f"  companies: {_rel(res['companies_path'])}")
    print(f"  manifest: {_rel(res['manifest_path'])}")
    print(f"  rows: {res['row_count']} / mapped: {res['mapped_securities_code_count']} / input_files: {res['input_file_count']}")
    print("  ※ raw本文・APIキー値は表示していません。売買指示・推奨・予測は生成していません。")


def cmd_research_queue(args) -> None:
    """Phase D0: deterministic research items from derived features. No LLM handoff."""
    asof = _valid_asof(args.asof)
    q = build_research_queue(asof=asof)
    res = write_research_queue(q)
    print(f"research queue を生成しました: {_rel(res['md_path'])} / {_rel(res['csv_path'])}")
    print(f"  items: {res['count']} / asof: {q['asof']}")
    print("  ※ 調査項目であり、売買指示ではありません。provider raw本文・LLM投入はしていません。")


def cmd_evidence(args) -> None:
    """Phase D0: deterministic evidence pack from derived features. No LLM handoff."""
    asof = _valid_asof(args.asof)
    ev = build_evidence(args.entity, asof=asof)
    res = write_evidence(ev)
    print(f"evidence を生成しました: {_rel(res['path'])}")
    print(f"  edinet_code: {res['edinet_code']} / asof: {ev['asof']}")
    print("  ※ raw本文は含めず、derived feature と hash/provenance参照だけを整理しています。")


def _parse_jquants_codes(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    codes = [c.strip().upper() for c in raw.split(",") if c.strip()]
    return codes or None


def cmd_jquants_evidence(args) -> None:
    """Point-in-time price evidence for one J-Quants securities code. No LLM, no network."""
    asof = _valid_asof(args.asof)
    ev = build_jquants_evidence(args.code, asof=asof)
    res = write_jquants_evidence(ev)
    print(f"J-Quants evidence を生成しました: {_rel(res['path'])}")
    print(f"  securities_code: {res['securities_code']} / asof: {ev['asof']}")
    print("  ※ 当時の株価(PIT)・指標の整理です。売買指示・順位・予測ではありません。")


def cmd_llm_brief(args) -> None:
    """Build a bounded LLM handoff packet. It does not call an LLM API."""
    asof = _valid_asof(args.asof)
    if args.max_items is not None and args.max_items <= 0:
        raise SystemExit("--max-items は正の整数で指定してください")
    packet = build_llm_handoff(asof=asof, max_items=args.max_items,
                               jquants_codes=_parse_jquants_codes(args.jquants_codes))
    res = write_llm_handoff(packet)
    print(f"LLM brief を生成しました: {_rel(res['md_path'])} / {_rel(res['manifest_path'])}")
    print(f"  evidence blocks: {res['count']} / J-Quants blocks: {res['jquants_count']} / asof: {packet['asof']}")
    print("  ※ LLM APIは呼んでいません。provider raw本文・APIキー値・.env は含めていません。")


def cmd_audit_report(args) -> None:
    """Aggregate EDINET×J-Quants cross-check + J-Quants valuation coverage.

    Discipline/honesty instrument: integrity check only, no ranking/advice.
    """
    asof = _valid_asof(args.asof)
    report = build_audit_report(asof=asof)
    res = write_audit_report(report)
    cc = report["cross_check"]
    val = report["valuation"]
    vr = val.get("valuation_coverage_ratio")
    print(f"data quality audit を生成しました: {_rel(res['md_path'])} / {_rel(res['manifest_path'])}")
    print(f"  cross-checked items: {cc.get('cross_checked_items', 0)} / metrics: {len(cc.get('metrics') or {})}")
    print(f"  valuation_coverage: {vr*100:.1f}%" if isinstance(vr, (int, float)) else "  valuation_coverage: UNKNOWN")
    print("  ※ 整合性の点検です。売買順・推奨・予測ではありません。")


def cmd_fetch_jquants(args) -> None:
    """Fetch a few codes from J-Quants REST and build derived features.

    Network egress lives in radar.sources; no API key / raw body is printed.
    Bridges the case where only REST access (not bulk) is available.
    """
    asof = _valid_asof(args.asof) or date.today().isoformat()
    codes = _parse_jquants_codes(args.codes)
    if not codes:
        raise SystemExit("--codes が必要です(例 7203,6758)")
    from .features.jquants_rest import fetch_and_build
    res = fetch_and_build(codes=codes, asof=asof)
    cov = res["coverage"]
    print(f"fetch-jquants: derived を生成しました（REST）: {_rel(res['features_path'])}")
    print(f"  codes: {res['feature_rows']} / price_covered: {cov['price_covered']}"
          f" / valuation_covered: {cov['valuation_covered']} / latest_price_date: {cov['latest_price_date']}")
    print("  ※ APIキー値・raw本文は表示していません。ランキング/推奨/予測は生成していません。")


def cmd_daily_update(args) -> None:
    """One-shot: derived features -> research-queue -> analysis brief for Claude.

    Does not call any LLM API and does not run network sync (run `sync` first).
    """
    asof = _valid_asof(args.asof)
    if args.max_items is not None and args.max_items <= 0:
        raise SystemExit("--max-items は正の整数で指定してください")
    result = run_daily_update(
        asof=asof,
        max_items=args.max_items,
        build_edinet=not args.no_edinet,
        build_jquants=not args.no_jquants,
        jquants_codes=_parse_jquants_codes(args.jquants_codes),
        dry_run=args.dry_run,
    )
    print(render_daily_summary(result), end="")
    if any(s.status == "failed" for s in result["steps"]):
        raise SystemExit("daily-update: 失敗ステップがあります(上記サマリ参照)")


def main() -> None:
    ap = argparse.ArgumentParser(prog="radar",
                                 description="Personal Equity Research Radar")
    sub = ap.add_subparsers(dest="command")
    pm = sub.add_parser("mirror", help="正直な集中度レポート(look-through)")
    pm.add_argument("--asof", help="基準日 YYYY-MM-DD(固定すると出力が再現可能)")
    pc = sub.add_parser("check", help='規律チェック。例: check buy 7203 100000 Financials [--overheated]')
    pc.add_argument("action", nargs=argparse.REMAINDER,
                    help='行動: buy/add/trim/exit <ticker> <金額> [sector] [--overheated --thesis-intact --powder]')
    pl = sub.add_parser("log", help="判断を decision_log.jsonl に追記(反証可能な予測が必須)")
    pl.add_argument("path", nargs="?", help="判断JSON(既定: journal/decision_input.json)")
    ps = sub.add_parser("score", help="期日到来分をDCA比で機械採点(未来不参照)")
    ps.add_argument("path", nargs="?", help="価格JSON(既定: journal/prices.json)")
    ps.add_argument("--asof", help="採点基準日 YYYY-MM-DD(既定: 今日)。過去固定で監査再現可能")
    sub.add_parser("review", help="較正レポート(裁量 vs 規律 / 対DCA)")
    pt = sub.add_parser("target-check",
                        help="目標倍率の必要条件/破綻条件を純計算で可視化(銘柄なし・推奨なし・予測なし)")
    pt.add_argument("--multiple", type=float, required=True, help="目標倍率(例 10)。1より大")
    pt.add_argument("--years", type=float, required=True, help="期間(年・例 10)")
    pt.add_argument("--monthly", type=float, default=0.0, help="月次積立(円・既定0)")
    pt.add_argument("--initial", type=float, default=None,
                    help="現資産(円・既定: portfolio.json 総額)")
    pt.add_argument("--taxable-frac", dest="taxable_frac", type=float, default=None,
                    help="課税口座の割合 0〜1(既定: portfolio から導出 / --initial 指定時は1.0)")
    pt.add_argument("--tax-rate", dest="tax_rate", type=float,
                    default=target_check.DEFAULT_TAX_RATE,
                    help=f"譲渡益税率(既定 {target_check.DEFAULT_TAX_RATE})")
    pt.add_argument("--leverage", type=float, default=1.0, help="レバレッジ倍率(既定1.0=無)")
    pt.add_argument("--max-dd", dest="max_dd", type=float, default=None,
                    help="最大ドローダウン許容%%(任意)")
    pt.add_argument("--asof", help="基準日 YYYY-MM-DD(再現可能性のため・任意)")
    pva = sub.add_parser("value-audit",
                         help="決算to決算の割安“仮説”検証(銘柄推奨なし・予測なし・購入意思でない)")
    vsub = pva.add_subparsers(dest="va_command")
    vr = vsub.add_parser("register", help="割安仮説を事前固定(紙上・手入力 --from-file)")
    vr.add_argument("ticker", nargs="?", help="ticker(--from-file と一致確認)")
    vr.add_argument("--from-file", dest="from_file", help="仮説JSON(Phase A は必須)")
    vr.add_argument("--asof", help="基準日 YYYY-MM-DD(PIT・再現性)")
    vsc = vsub.add_parser("score", help="次決算後の手入力実績で事後採点(対DCA=UNKNOWN)")
    vsc.add_argument("--from-file", dest="from_file", help="採点JSON(Phase A は必須)")
    vsc.add_argument("--asof", help="採点基準日 YYYY-MM-DD(既定: 入力の asof)")
    vrv = vsub.add_parser("review", help="較正(固定表示順・hit率を煽らない)")
    vrv.add_argument("--asof", help="基準日 YYYY-MM-DD(任意)")
    pd = sub.add_parser("data-check",
                        help="(A0)--offline でキー存在/redact確認 /(A1)--live で軽量疎通のみ")
    mode = pd.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="ネット無しでキー存在/redactを確認")
    mode.add_argument("--live", action="store_true", help="(A1)軽量疎通のみ。本文は保存/表示/LLM投入しない")
    pd.add_argument("--provider", choices=["jquants", "edinet-db"], help="--live の対象")
    psy = sub.add_parser("sync",
                         help="(Phase B) edinet-db companies/financials の最小raw sync。本文は表示/LLM投入しない")
    psy.add_argument("--provider", required=True, choices=["edinet-db"], help="Phase B最小syncは edinet-db のみ")
    psy.add_argument("--dataset", required=True, choices=["companies", "financials"],
                     help="Phase B最小syncは companies|financials のみ")
    psy.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 今日)。available_at<=asof のみ保存")
    psy.add_argument("--page", type=int, default=edinet_db.DEFAULT_PAGE, help="取得ページ(正の整数)")
    psy.add_argument("--per-page", dest="per_page", type=int, default=edinet_db.DEFAULT_PER_PAGE,
                     help="companies用: 1ページ件数(正の整数)")
    psy.add_argument("--code", help="financials用: EDINETコード(E02367形式)")
    psy.add_argument("--codes-file", dest="codes_file",
                     help="financials batch用: data/metadata 配下のEDINETコード一覧(1行1コード)")
    psy.add_argument("--offset", type=int, default=0,
                     help="financials batch用: codes-file の開始位置(0以上)")
    psy.add_argument("--limit", type=int, default=None,
                     help="financials batch用: 最大取得件数(data_layer.daily_request_budget 以下)")
    psy.add_argument("--years", type=int, default=edinet_db.DEFAULT_YEARS, help="financials用: 取得年数(正の整数)")
    psy.add_argument("--period", choices=edinet_db.PERIODS, default="annual",
                     help="financials用: annual|quarterly|quarterly_standalone")
    pbf = sub.add_parser("build-features",
                         help="(Phase C) edinet-db financials raw から derived feature を生成(推奨/予測なし)")
    pbf.add_argument("--provider", required=True, choices=["edinet-db"], help="Phase C minimal は edinet-db のみ")
    pbf.add_argument("--dataset", required=True, choices=["financials"], help="Phase C minimal は financials のみ")
    pbf.add_argument("--raw-path", help="data/raw/edinet-db/financials 配下の raw JSON")
    pbf.add_argument("--raw-dir", help="data/raw/edinet-db/financials/<asof> ディレクトリをbatch処理")
    pbf.add_argument("--limit", type=int, default=None, help="batch処理の最大件数(任意・正の整数)")
    pbf.add_argument("--asof", required=True, help="基準日 YYYY-MM-DD。available_at<=asof のみ採用")
    pjq = sub.add_parser(
        "build-jquants-features",
        help="取得済み J-Quants Bulk からローカルderived featureを生成(ネット/APIキーなし)",
        description="取得済み J-Quants Bulk からローカルderived featureを生成します。ランキング/推奨/予測は出しません。",
    )
    pjq.add_argument("--asof", required=True, help="基準日 YYYY-MM-DD。asof以前のbulk行のみ採用")
    pcm = sub.add_parser(
        "build-company-map",
        help="EDINET companies raw から EDINETコード↔証券コードのderived mapを生成(ネット/APIキーなし)",
        description="EDINET companies raw から research/evidence 用のコード対応表を生成します。売買指示・推奨・予測は出しません。",
    )
    pcm.add_argument("--raw-dir", required=True, help="data/raw/edinet-db/companies/<asof> ディレクトリ")
    pcm.add_argument("--asof", required=True, help="基準日 YYYY-MM-DD")
    prq = sub.add_parser("research-queue",
                         help="(Phase D0) derived feature から調査項目を生成(売買指示なし・LLM投入なし)")
    prq.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 最新の derived asof)")
    pev = sub.add_parser("evidence",
                         help="(Phase D0) EDINET code の evidence pack を生成(売買指示なし・LLM投入なし)")
    pev.add_argument("entity", help="EDINETコード(E02367形式)。Phase D0 は ticker未対応")
    pev.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 最新の derived asof)")
    plb = sub.add_parser("llm-brief",
                         help="(Phase D1 prep) derived/evidence からLLM投入用packetを生成(API呼び出しなし)")
    plb.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 最新の derived asof)")
    plb.add_argument("--max-items", dest="max_items", type=int, default=None,
                     help="packetに含める最大件数(任意・正の整数)")
    plb.add_argument("--jquants-codes", dest="jquants_codes", default=None,
                     help="当時の株価を載せる証券コード(カンマ区切り 例 7203,6758)")
    pje = sub.add_parser("jquants-evidence",
                         help="J-Quants 証券コードの当時の株価(PIT)evidenceを生成(LLM/ネットなし)")
    pje.add_argument("code", help="証券コード(例 7203)")
    pje.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 最新の jquants derived asof)")
    par = sub.add_parser("audit-report",
                         help="EDINET×J-Quants 整合と valuation coverage を集計(整合点検・売買順なし)")
    par.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 最新の derived asof)")
    pfj = sub.add_parser("fetch-jquants",
                         help="J-Quants REST から指定銘柄を取得し derived を生成(.env認証・ネットあり)")
    pfj.add_argument("--codes", required=True, help="証券コード(カンマ区切り 例 7203,6758)")
    pfj.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 今日)。asof以前のみ採用")
    pdu = sub.add_parser(
        "daily-update",
        help="(運用) derived→research→分析パケットを一括生成しClaude分析用に出力(LLM API呼び出しなし)")
    pdu.add_argument("--asof", help="基準日 YYYY-MM-DD(既定: 今日)")
    pdu.add_argument("--max-items", dest="max_items", type=int, default=None,
                     help="briefに含める最大件数(任意・正の整数)")
    pdu.add_argument("--jquants-codes", dest="jquants_codes", default=None,
                     help="当時の株価を載せる証券コード(カンマ区切り 例 7203,6758)")
    pdu.add_argument("--no-edinet", dest="no_edinet", action="store_true",
                     help="EDINET financials の feature 生成をスキップ")
    pdu.add_argument("--no-jquants", dest="no_jquants", action="store_true",
                     help="J-Quants bulk の feature 生成をスキップ")
    pdu.add_argument("--dry-run", dest="dry_run", action="store_true",
                     help="計画だけ表示(書込・生成しない)")
    args = ap.parse_args()

    if args.command == "mirror":
        cmd_mirror(args.asof)
    elif args.command == "check":
        if not args.action:
            raise SystemExit('例: python3 -m radar check buy 7203 100000 Financials')
        cmd_check(args.action)
    elif args.command == "log":
        cmd_log(args.path)
    elif args.command == "score":
        cmd_score(args.path, args.asof)
    elif args.command == "review":
        cmd_review()
    elif args.command == "target-check":
        cmd_target_check(args)
    elif args.command == "value-audit":
        cmd_value_audit(args)
    elif args.command == "data-check":
        cmd_data_check(args.offline, live=args.live, provider=args.provider)
    elif args.command == "sync":
        cmd_sync(args)
    elif args.command == "build-features":
        cmd_build_features(args)
    elif args.command == "build-jquants-features":
        cmd_build_jquants_features(args)
    elif args.command == "build-company-map":
        cmd_build_company_map(args)
    elif args.command == "research-queue":
        cmd_research_queue(args)
    elif args.command == "evidence":
        cmd_evidence(args)
    elif args.command == "llm-brief":
        cmd_llm_brief(args)
    elif args.command == "jquants-evidence":
        cmd_jquants_evidence(args)
    elif args.command == "audit-report":
        cmd_audit_report(args)
    elif args.command == "fetch-jquants":
        cmd_fetch_jquants(args)
    elif args.command == "daily-update":
        cmd_daily_update(args)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
