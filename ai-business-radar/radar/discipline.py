"""規律エンジン(純粋)。提案された行動を、宣言的ルールに照らして判定する。

ハード却下(ok=False): 1銘柄上限 / セクター上限 / 個別株合計上限の超過、
                       セクター不明(評価不能)、過熱(--overheated)、
                       ナンピンの3条件未充足、不正な金額。
ソフト警告: 勝ち銘柄への買い増し(a/c)。
価格APIは使わず、取得原価 vs 時価で「勝ち/負けの買い増し」を判定(ファイル=真実)。
過熱の自動判定は価格パイプライン実装後(Phase後段)。当面は --overheated フラグで明示。

行動の文法:
  <verb> <ticker> <amount_jpy> [sector] [--overheated] [--thesis-intact] [--powder]
  verb = buy | add | trim | exit
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DISCIPLINE = {"chase_unrealized_pct": 0.25, "averaging_down_pct": -0.25}
KNOWN_FLAGS = {"--overheated", "--thesis-intact", "--powder", "--cost-unknown-ok"}


def _thesis_sector(ticker: str | None) -> str | None:
    if not ticker:
        return None
    p = ROOT / "thesis" / f"{ticker}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("sector")
        except json.JSONDecodeError:
            return None
    return None


def _num(v):
    """数値フィールドを安全に取り出す。bool/非数値/非有限(nan,inf)は None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    return None


def _satellite_state(portfolio: dict):
    """総額と、個別株の銘柄別・セクター別集計を返す。同一tickerが複数口座にあれば合算。"""
    total = 0.0
    names: dict = {}
    sectors: dict = {}
    for h in portfolio.get("holdings", []):
        mv = _num(h.get("market_value_jpy"))
        if mv is None:
            raise SystemExit(f"portfolio: market_value_jpy が有限な数値でない: {h.get('ticker')}")
        if mv < 0:
            raise SystemExit(f"portfolio: market_value_jpy が負: {h.get('ticker')}")
        total += mv
        if h.get("kind") == "individual_stock":
            tk = h.get("ticker", "?")
            sec = h.get("sector", "unknown")
            cost = _num(h.get("cost_basis_jpy"))
            if tk in names:  # 複数口座の同一銘柄を合算
                e = names[tk]
                e["value"] += mv
                e["cost"] = (e["cost"] + cost) if (e["cost"] is not None and cost is not None) else None
            else:
                names[tk] = {"value": mv, "sector": sec, "cost": cost}
            sectors[sec] = sectors.get(sec, 0) + mv
    return total, names, sectors


def parse_action(s: str) -> dict:
    tokens = s.split()
    flags = {t for t in tokens if t.startswith("--")}
    parts = [t for t in tokens if not t.startswith("--")]
    unknown_flags = flags - KNOWN_FLAGS
    if not parts:
        raise SystemExit('行動を指定: 例 `buy 7203 100000 Financials`')
    verb = parts[0].lower()
    ticker = parts[1].upper() if len(parts) > 1 else None
    amount = None
    if len(parts) > 2:
        try:
            amount = float(parts[2])
        except ValueError:
            raise SystemExit(f"金額が数値ではありません: {parts[2]}")
    sector = parts[3] if len(parts) > 3 else None
    return {"verb": verb, "ticker": ticker, "amount": amount, "sector": sector,
            "flags": flags, "unknown_flags": unknown_flags, "extra": parts[4:]}


def check(portfolio: dict, cfg: dict, action_str: str) -> dict:
    sat = cfg["policy"]["satellite"]
    disc = {**DEFAULT_DISCIPLINE, **cfg["policy"].get("discipline", {})}
    act = parse_action(action_str)
    verb, tk, amt, sec, flags = (act["verb"], act["ticker"], act["amount"],
                                 act["sector"], act["flags"])
    total, names, sectors = _satellite_state(portfolio)
    cur = names.get(tk)
    if cur:
        sec = cur["sector"]
    elif not sec:
        sec = _thesis_sector(tk)  # None の可能性

    breaches: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []
    if act["unknown_flags"]:
        raise SystemExit(f"未知のフラグ: {sorted(act['unknown_flags'])}(typoの可能性。既知: {sorted(KNOWN_FLAGS)})")
    if act["extra"]:
        raise SystemExit(f"余分なトークン: {act['extra']}(文法: <verb> <ticker> <金額> [sector] [flags])")

    if verb in ("buy", "add"):
        if amt is None:
            raise SystemExit("金額を指定: 例 `buy 7203 100000 Financials`")
        if not math.isfinite(amt) or amt <= 0:
            raise SystemExit(f"金額は有限の正の数で指定してください: {amt}")
        if total <= 0:
            raise SystemExit("ポートフォリオ総額が 0 以下です(portfolio を確認)")

        new_total = total + amt  # 新規資金の想定(分母も増える)
        new_name = (cur["value"] if cur else 0) + amt
        new_sector = (sectors.get(sec, 0) if sec else 0) + amt
        new_individual = sum(n["value"] for n in names.values()) + amt
        name_pct = new_name / new_total * 100
        sector_pct = new_sector / new_total * 100
        ind_pct = new_individual / new_total * 100

        if ind_pct > sat["max_pct_of_total"]:
            breaches.append(f"個別株合計 {ind_pct:.1f}% > 上限 {sat['max_pct_of_total']}%")
        if name_pct > sat["max_pct_per_name"]:
            breaches.append(f"{tk} {name_pct:.1f}% > 1銘柄上限 {sat['max_pct_per_name']}%")
        # セクター不明は“評価不能のまま通す”を禁止 → 却下(Codex #7)
        if not sec or sec == "unknown":
            breaches.append("セクター不明 → セクター上限を評価不可。sector を指定するか thesis に記入(却下)")
        elif sector_pct > sat["max_pct_per_sector"]:
            breaches.append(f"セクター {sec} {sector_pct:.1f}% > 上限 {sat['max_pct_per_sector']}%")

        # 過熱(失敗a): 自動判定は後段、当面はフラグで明示 → ハード却下
        if "--overheated" in flags:
            breaches.append("過熱(--overheated)→ 新規/買い増しを却下(失敗a: 飛びつき)。押し目・落ち着きを待つ")

        # 取得原価 vs 時価(勝ち=chase / 負け=ナンピン)
        if cur:
            cost = cur.get("cost")
            if not cost:  # None または 0
                if "--cost-unknown-ok" in flags:
                    notes.append("cost_basis 未記入だが --cost-unknown-ok で続行(勝ち/ナンピン判定なし)")
                else:
                    breaches.append("cost_basis_jpy 未記入/0 → 勝ち買い増し/ナンピンを判定できず却下。"
                                    "cost_basis_jpy を記入するか、承知の上なら --cost-unknown-ok を明示。")
            else:
                unreal = (cur["value"] - cost) / cost
                if unreal > disc["chase_unrealized_pct"]:
                    warnings.append(f"勝ち銘柄への買い増し(含み益 +{unreal*100:.0f}%)= 失敗a/c。"
                                    "『好調だから買い増し』。確信は上限を緩めない。")
                elif unreal < disc["averaging_down_pct"]:
                    # ナンピンの3条件: 仮説無傷 + 事前余力 + 上限内(上限は上の breaches で担保)
                    ok3 = ("--thesis-intact" in flags) and ("--powder" in flags)
                    if not ok3:
                        breaches.append(
                            f"ナンピン(含み損 {unreal*100:.0f}%)→ 3条件未充足で却下。"
                            "必要: 仮説無傷(--thesis-intact)+ 事前余力(--powder)+ 上限内。"
                            "価格でなく『仮説が無傷か』で判断。")
                    else:
                        warnings.append(f"ナンピン(含み損 {unreal*100:.0f}%): 3条件は申告済み。"
                                        "最終判断は『価格』でなく『仮説』で。上限は厳守。")

        if not cur and sec and sec != "unknown" and sec in sectors:
            notes.append(f"同一セクター({sec})に既存保有あり → 独立した賭けか確認")
        if sat.get("universe") == "JP_individual" and tk and not tk.isdigit():
            notes.append(f"方針は日本企業(中小型)。{tk} は universe(JP_individual)外の可能性")

    elif verb in ("trim", "sell", "exit"):
        if amt is not None or flags:
            notes.append("trim/exit では金額・フラグは判定に未使用(注記のみ)")
        notes.append("リスクを下げる方向。売り基準は『仮説崩壊 / 上限超のトリム / 資金需要』のいずれかか?")
        if cur and cur.get("cost") and cur["value"] > cur["cost"]:
            notes.append("勝ち銘柄の売却 → 失敗d(早すぎる利確)に注意。"
                         "上限超のトリムなら可、ただの利確衝動なら見送り。")
        if not cur:
            notes.append(f"{tk} は現在のサテライトに無い。")
    else:
        raise SystemExit(f"未知の行動: {verb}(buy / add / trim / exit)")

    return {"ok": len(breaches) == 0, "action": act, "sector_used": sec or "unknown",
            "breaches": breaches, "warnings": warnings, "notes": notes}
