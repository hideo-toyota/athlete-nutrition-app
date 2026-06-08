"""look-through 集中度の算出(純粋・決定論 / 原則3の心臓)。

指数ファンドは中身(指数構成)まで展開して、direct 保有と合算する。
これにより「見えない総集中度」(例: 円建てインデックス経由のUSD/米テック)が見える。
"""
from __future__ import annotations

from .data import load_index


def _add(d: dict, k: str, v: float) -> None:
    d[k] = d.get(k, 0.0) + v


def look_through(portfolio: dict, cfg: dict) -> dict:
    holdings = portfolio.get("holdings", [])
    total = sum(h.get("market_value_jpy", 0) for h in holdings)
    if total <= 0:
        raise SystemExit("ポートフォリオ総額が 0 です")

    by_name: dict = {}
    by_sector: dict = {}
    by_region: dict = {}
    by_currency: dict = {}

    # direct な個別株(=サテライト)。上限チェックはここに効かせる。
    sat_by_name: dict = {}
    sat_by_sector: dict = {}
    individual_total = 0.0

    for h in holdings:
        mv = h.get("market_value_jpy", 0)
        kind = h.get("kind")
        if kind == "individual_stock":
            individual_total += mv
            _add(sat_by_name, h["ticker"], mv)
            _add(sat_by_sector, h.get("sector", "unknown"), mv)
            _add(by_name, h["ticker"], mv)
            _add(by_sector, h.get("sector", "unknown"), mv)
            _add(by_region, h.get("region", "unknown"), mv)
            _add(by_currency, h.get("currency", "unknown"), mv)
        elif kind in ("index_fund", "etf"):
            ref = h.get("composition_ref")
            if not ref:
                _add(by_sector, "指数(構成不明)", mv)
                _add(by_currency, h.get("currency", "JPY"), mv)
                continue
            idx = load_index(ref)
            top = idx.get("top_holdings", {})
            for tk, w in top.items():
                _add(by_name, tk, mv * w)
            _add(by_name, "その他(指数・分散)", mv * max(0.0, 1 - sum(top.values())))
            for sec, w in idx.get("sector_weights", {}).items():
                _add(by_sector, sec, mv * w)
            for reg, w in idx.get("region_weights", {}).items():
                _add(by_region, reg, mv * w)
            for cur, w in idx.get("currency_weights", {}).items():
                _add(by_currency, cur, mv * w)
        else:  # cash 等
            _add(by_currency, h.get("currency", "JPY"), mv)
            _add(by_sector, "現金等", mv)

    def pct(d: dict) -> dict:
        return {k: v / total * 100 for k, v in d.items()}

    sat = cfg["policy"]["satellite"]
    name_breaches = {tk: v / total * 100 for tk, v in sat_by_name.items()
                     if v / total * 100 > sat["max_pct_per_name"]}
    sector_breaches = {s: v / total * 100 for s, v in sat_by_sector.items()
                       if v / total * 100 > sat["max_pct_per_sector"]}
    individual_pct = individual_total / total * 100
    n_names = len(sat_by_name)

    return {
        "total_jpy": total,
        "lookthrough": {
            "by_sector": pct(by_sector),
            "by_region": pct(by_region),
            "by_currency": pct(by_currency),
            "by_name": pct(by_name),
        },
        "satellite": {
            "individual_pct": individual_pct,
            "n_names": n_names,
            "by_name_pct": {k: v / total * 100 for k, v in sat_by_name.items()},
            "by_sector_pct": {k: v / total * 100 for k, v in sat_by_sector.items()},
            "caps": sat,
            "name_breaches": name_breaches,
            "sector_breaches": sector_breaches,
            "over_total_cap": individual_pct > sat["max_pct_of_total"],
            "under_min_names": 0 < n_names < sat.get("min_names", 0),
        },
    }
