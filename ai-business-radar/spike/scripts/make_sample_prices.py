#!/usr/bin/env python3
"""合成サンプル株価データ(日足OHLCV)を生成する開発用スクリプト。

ネットや J-Quants キーが無くても trend / backtest-trend を試せるように、
data/prices/ に決定論的(seed固定)なサンプルCSVを書き出す。
これは学習用のダミーであり、実在企業・実データではありません。

実行: python3 scripts/make_sample_prices.py
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRICE_DIR = ROOT / "data" / "prices"
N_DAYS = 520  # 約2年分の営業日
END = date(2026, 6, 5)


def business_days(end: date, n: int) -> list[date]:
    days: list[date] = []
    d = end
    while len(days) < n:
        if d.weekday() < 5:  # Mon-Fri
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


def gen_series(seed: int, start: float, drift: float, vol: float,
               base_volume: int, profile: str) -> list[dict]:
    rnd = random.Random(seed)
    dates = business_days(END, N_DAYS)
    rows = []
    close = start
    prev_close = start
    final_ramp = N_DAYS - 6   # hot: 終盤6日は押し目なしのクリーンな急騰
    spike_start = N_DAYS - 18
    for i, d in enumerate(dates):
        daily_drift = drift
        v_mult = 1.0

        # hot プロファイル: 終盤に押し目なしの急騰(=過熱)を確実に作る
        if profile == "hot" and i >= final_ramp:
            close = prev_close * 1.05
            op = prev_close * 1.002
            hi = close * 1.01
            lo = op * 0.999
            volume = int(base_volume * 4 * rnd.uniform(0.9, 1.1))
            rows.append({
                "date": d.isoformat(),
                "open": round(op, 1), "high": round(hi, 1),
                "low": round(lo, 1), "close": round(close, 1), "volume": volume,
            })
            prev_close = close
            continue

        if profile == "hot":
            daily_drift = 0.006 if i >= spike_start else -0.0002
            if i >= spike_start:
                v_mult = 2.5
        elif profile == "range":
            daily_drift = 0.0
        ret = daily_drift + rnd.gauss(0, vol)
        close = max(1.0, prev_close * (1 + ret))
        gap = rnd.gauss(0, vol * 0.4)
        op = max(1.0, prev_close * (1 + gap))
        hi = max(op, close) * (1 + abs(rnd.gauss(0, vol * 0.6)))
        lo = min(op, close) * (1 - abs(rnd.gauss(0, vol * 0.6)))
        vol_noise = rnd.uniform(0.6, 1.4)
        volume = int(base_volume * v_mult * vol_noise)
        rows.append({
            "date": d.isoformat(),
            "open": round(op, 1),
            "high": round(hi, 1),
            "low": round(lo, 1),
            "close": round(close, 1),
            "volume": volume,
        })
        prev_close = close
    return rows


def write_csv(name: str, rows: list[dict]) -> None:
    PRICE_DIR.mkdir(parents=True, exist_ok=True)
    path = PRICE_DIR / f"{name}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def main() -> None:
    # ベンチマーク(TOPIX proxy): ゆるやかな上昇
    write_csv("BENCHMARK", gen_series(1, 2700, 0.00035, 0.008, 1000000, "normal"))
    # 強い上昇トレンド
    write_csv("SAMPLE-A", gen_series(11, 900, 0.0013, 0.018, 800000, "up"))
    # 低ボラの緩やかな上昇(ETF的)
    write_csv("SAMPLE-ETF", gen_series(22, 2800, 0.0009, 0.006, 1200000, "up"))
    # 材料株/PTS急騰タイプ(過熱)
    write_csv("SAMPLE-HOT", gen_series(33, 1200, 0.0, 0.02, 300000, "hot"))
    # 下落トレンド
    write_csv("SAMPLE-DOWN", gen_series(44, 2000, -0.0011, 0.016, 500000, "down"))


if __name__ == "__main__":
    main()
