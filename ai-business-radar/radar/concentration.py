"""look-through 集中度の算出(純粋・決定論 / 原則3の心臓)。

指数ファンドは中身(指数構成)まで展開して、direct 保有と合算する。
これにより「見えない総集中度」(例: 円建てインデックス経由のUSD/米テック)が見える。
"""
from __future__ import annotations

import math
from datetime import date

from .data import load_index


def _add(d: dict, k: str, v: float) -> None:
    d[k] = d.get(k, 0.0) + v


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v if math.isfinite(v) else None
    return None


def _asof_tuple(s):
    """'2026-06-06' / '2026/06' / '2026' を比較可能な (y,m,d) に。不正値は None。"""
    if not s:
        return None
    parts = str(s).replace("/", "-").split("-")
    try:
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 1
        d = int(parts[2]) if len(parts) > 2 else 1
    except (ValueError, IndexError):
        return None
    try:
        date(y, m, d)  # 実在日のみ(2026-02-31 / year0 は弾く)
    except ValueError:
        return None
    return (y, m, d)


def look_through(portfolio: dict, cfg: dict) -> dict:
    holdings = portfolio.get("holdings", [])
    port_as_of = portfolio.get("as_of")
    total = 0.0
    for h in holdings:
        mv = _num(h.get("market_value_jpy"))
        if mv is None:
            raise SystemExit(f"portfolio: market_value_jpy が有限な数値でない: {h.get('ticker')}")
        if mv < 0:
            raise SystemExit(f"portfolio: market_value_jpy が負: {h.get('ticker')}")
        total += mv
    if total <= 0:
        raise SystemExit("ポートフォリオ総額が 0 以下です")

    by_name: dict = {}
    by_sector: dict = {}
    by_region: dict = {}
    by_currency: dict = {}
    sat_by_name: dict = {}
    sat_by_sector: dict = {}
    individual_total = 0.0
    index_meta: list = []
    data_warnings: list = []

    for h in holdings:
        mv = _num(h.get("market_value_jpy")) or 0
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
                data_warnings.append(f"{h.get('ticker')}: 指数構成(composition_ref)が無く、look-through できない")
                continue
            idx = load_index(ref)
            sw = idx.get("sector_weights", {})
            rw = idx.get("region_weights", {})
            cw = idx.get("currency_weights", {})
            top = idx.get("top_holdings", {})
            idx_as_of = idx.get("as_of")
            for label, wd in (("sector_weights", sw), ("region_weights", rw),
                              ("currency_weights", cw), ("top_holdings", top)):
                if not isinstance(wd, dict):
                    raise SystemExit(f"指数 {ref} の {label} は object である必要があります")
                for kk, w in wd.items():
                    if not (isinstance(w, (int, float)) and not isinstance(w, bool) and math.isfinite(w)):
                        raise SystemExit(f"指数 {ref} の {label}[{kk}] が有限な数値でない: {w!r}")
            index_meta.append({"ref": ref, "as_of": idx_as_of,
                               "sector_sum": sum(sw.values()),
                               "region_sum": sum(rw.values()),
                               "currency_sum": sum(cw.values()),
                               "top_sum": sum(top.values())})
            it, pt = _asof_tuple(idx_as_of), _asof_tuple(port_as_of)
            if it and pt and it > pt:
                raise SystemExit(
                    f"指数 {ref} の as_of({idx_as_of})がポートフォリオ as_of({port_as_of})より新しいため停止"
                )
            if idx_as_of and it is None:
                data_warnings.append(f"指数 {ref} の as_of '{idx_as_of}' が解釈不能(鮮度を確認できない)")
            if not sw and not rw and not cw and not top:
                data_warnings.append(f"指数 {ref} の構成が空(look-through できない)")
            for label, s in (("セクター", sum(sw.values())), ("地域", sum(rw.values())),
                             ("通貨", sum(cw.values()))):
                if s and abs(s - 1.0) > 0.05:
                    data_warnings.append(f"指数 {ref} の{label}ウェイト合計が {s:.2f}(≠1.0)")
            for label, d in (("セクター", sw), ("地域", rw), ("通貨", cw), ("上位銘柄", top)):
                if any((w is None) or (isinstance(w, (int, float)) and w < 0) for w in d.values()):
                    data_warnings.append(f"指数 {ref} の{label}に負/不正なウェイトがある")
            if sum(v for v in top.values() if isinstance(v, (int, float))) > 1.001:
                data_warnings.append(
                    f"指数 {ref} の上位銘柄ウェイト合計が {sum(top.values()):.2f}(>1)→ 銘柄別exposureが過大の恐れ")
            for tk, w in top.items():
                _add(by_name, tk, mv * w)
            _add(by_name, "その他(指数・分散)", mv * max(0.0, 1 - sum(top.values())))
            for sec, w in sw.items():
                _add(by_sector, sec, mv * w)
            for reg, w in rw.items():
                _add(by_region, reg, mv * w)
            for cur, w in cw.items():
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
        "port_as_of": port_as_of,
        "index_meta": index_meta,
        "data_warnings": data_warnings,
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
