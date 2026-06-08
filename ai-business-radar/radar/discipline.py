"""規律エンジン(純粋)。提案された行動を、宣言的ルールに照らして判定する。

ハード却下(ok=False): 1銘柄上限 / セクター上限 / 個別株合計上限の超過。
ソフト警告: 勝ち銘柄への買い増し(a/c)、ナンピン(価格でなく仮説で判断)。
価格APIは使わず、ポートフォリオの取得原価 vs 時価で「勝ち/負けの買い増し」を判定(ファイル=真実)。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


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


def _satellite_state(portfolio: dict):
    total = sum(h.get("market_value_jpy", 0) for h in portfolio.get("holdings", []))
    names: dict = {}
    sectors: dict = {}
    for h in portfolio.get("holdings", []):
        if h.get("kind") == "individual_stock":
            tk = h["ticker"]
            mv = h.get("market_value_jpy", 0)
            names[tk] = {"value": mv, "sector": h.get("sector", "unknown"),
                         "cost": h.get("cost_basis_jpy")}
            sectors[h.get("sector", "unknown")] = sectors.get(h.get("sector", "unknown"), 0) + mv
    return total, names, sectors


def parse_action(s: str) -> dict:
    parts = s.split()
    if not parts:
        raise SystemExit('行動を指定: 例 `buy 7203 100000 Financials`')
    verb = parts[0].lower()
    ticker = parts[1].upper() if len(parts) > 1 else None
    amount = None
    if len(parts) > 2:
        try:
            amount = float(parts[2])
        except ValueError:
            amount = None
    sector = parts[3] if len(parts) > 3 else None
    return {"verb": verb, "ticker": ticker, "amount": amount, "sector": sector}


def check(portfolio: dict, cfg: dict, action_str: str) -> dict:
    sat = cfg["policy"]["satellite"]
    act = parse_action(action_str)
    verb, tk, amt, sec = act["verb"], act["ticker"], act["amount"], act["sector"]
    total, names, sectors = _satellite_state(portfolio)
    cur = names.get(tk)
    if cur:
        sec = cur["sector"]
    elif not sec:
        sec = _thesis_sector(tk) or "unknown"

    breaches: list[str] = []
    warnings: list[str] = []
    notes: list[str] = []

    if verb in ("buy", "add"):
        if amt is None:
            raise SystemExit("金額を指定: 例 `buy 7203 100000`")
        new_total = total + amt  # 新規資金の想定(分母も増える)
        new_name = (cur["value"] if cur else 0) + amt
        new_sector = sectors.get(sec, 0) + amt
        new_individual = sum(n["value"] for n in names.values()) + amt
        name_pct = new_name / new_total * 100
        sector_pct = new_sector / new_total * 100
        ind_pct = new_individual / new_total * 100

        if ind_pct > sat["max_pct_of_total"]:
            breaches.append(f"個別株合計 {ind_pct:.1f}% > 上限 {sat['max_pct_of_total']}%")
        if name_pct > sat["max_pct_per_name"]:
            breaches.append(f"{tk} {name_pct:.1f}% > 1銘柄上限 {sat['max_pct_per_name']}%")
        if sec == "unknown":
            notes.append("セクター不明 → セクター上限を評価不可(thesis に sector を)")
        elif sector_pct > sat["max_pct_per_sector"]:
            breaches.append(f"セクター {sec} {sector_pct:.1f}% > 上限 {sat['max_pct_per_sector']}%")

        # 勝ち/負けへの買い増し(取得原価 vs 時価)
        if cur and cur.get("cost"):
            unreal = (cur["value"] - cur["cost"]) / cur["cost"]
            if unreal > 0.25:
                warnings.append(f"勝ち銘柄への買い増し(含み益 +{unreal*100:.0f}%)= 失敗a/c。"
                                "『好調だから買い増し』。確信は上限を緩めない。")
            elif unreal < -0.25:
                warnings.append(f"ナンピン(含み損 {unreal*100:.0f}%)= 価格でなく『仮説が無傷か』で判断。"
                                "許容は3条件: 仮説無傷 + 上限内 + 事前に確保した余力。")
        if not cur and sec != "unknown" and sec in sectors:
            notes.append(f"同一セクター({sec})に既存保有あり → 独立した賭けか確認")
        if sat.get("universe") == "JP_individual" and tk and not tk.isdigit():
            notes.append(f"方針は日本企業(中小型)。{tk} は universe(JP_individual)外の可能性")

    elif verb in ("trim", "sell", "exit"):
        notes.append("リスクを下げる方向。売り基準は『仮説崩壊 / 上限超のトリム / 資金需要』のいずれかか?")
        if cur and cur.get("cost") and cur["value"] > cur["cost"]:
            notes.append("勝ち銘柄の売却 → 失敗d(早すぎる利確)に注意。"
                         "上限超のトリムならOK、ただの利確衝動なら見送り。")
        if not cur:
            notes.append(f"{tk} は現在のサテライトに無い。")
    else:
        raise SystemExit(f"未知の行動: {verb}(buy / add / trim / exit)")

    return {"ok": len(breaches) == 0, "action": act, "sector_used": sec,
            "breaches": breaches, "warnings": warnings, "notes": notes}
