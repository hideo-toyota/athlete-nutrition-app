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
from .report import render_check, render_mirror, render_review, render_target_check

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


def cmd_data_check(offline: bool) -> None:
    """A0: ネットワーク無しのキー存在確認 + redact 動作確認。**値は表示しない・外部接続しない**。"""
    if not offline:
        raise SystemExit("A0: 実疎通は未実装です。`data-check --offline` で実行してください(実API疎通は A1)。")
    import os
    from .sources import common
    common._load_dotenv()
    for name in common.KEY_VARS:
        print(f"  {name}: {'設定あり' if os.environ.get(name) else '未設定'}")  # ★値は出さない
    sample = "Authorization: Bearer DUMMY.TOKEN.VALUE"
    print(f"  redact動作: {common.redact(sample)}")
    print("  ※ 外部APIには接続していません(A0)。実疎通は A1 で追加。")


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
    pd = sub.add_parser("data-check", help="(A0) キー存在とredactをオフライン確認。実疎通はしない")
    pd.add_argument("--offline", action="store_true", help="A0では必須。外部接続せずに確認")
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
    elif args.command == "data-check":
        cmd_data_check(args.offline)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
