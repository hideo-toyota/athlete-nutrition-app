"""トレンド・シグナルの簡易バックテスト(標準ライブラリのみ)。

ルール:
  - 各営業日 t で、t までのデータのみを使ってトレンドスコアを計算(未来データ不使用)。
  - スコアが entry_threshold 以上になったら、翌営業日にエントリー(寄付 or 終値)。
  - 決済: 損切り / 利確 / 最大保有日数 / スコアが exit_threshold を下回る、のいずれか。
    決済判断も t の終値で行い、執行は t+1。
  - 手数料・スリッページを往復で控除。
  - 学習期間(train)と検証期間(test=アウトオブサンプル)に分けて集計。
  - ベンチマークの同期間バイ&ホールドと比較。

⚠️ 簡易検証です。過去の結果は将来を保証しません。過剰最適化に注意してください。
"""
from __future__ import annotations

import math

import trend_indicators as ti

DEFAULTS = {
    "entry_threshold": 70,
    "exit_threshold": 50,
    "entry": "next_open",      # next_open | next_close
    "stop_loss_pct": 0.08,
    "take_profit_pct": 0.20,
    "hold_max_days": 40,
    "fee_rate": 0.001,         # 片道手数料
    "slippage_rate": 0.001,    # 片道スリッページ
    "train_end": None,         # "YYYY-MM-DD"。これ以前を学習、以降を検証
}


def _exec_price(bars, idx, mode):
    return bars[idx]["open"] if mode == "next_open" else bars[idx]["close"]


def run_backtest(bars, bench_bars, trend_params, bt_params):
    p = {**DEFAULTS, **(bt_params or {})}
    cost = p["fee_rate"] + p["slippage_rate"]  # 片道コスト率
    n = len(bars)
    need = max(ti.DEFAULTS["ma_windows"]) + ti.DEFAULTS["slope_window"] + 1
    trades = []

    in_pos = False
    entry_idx = entry_price = 0
    i = need
    while i < n - 1:  # t+1 で執行するため最後の1本は除く
        m = ti.compute_indicators(bars, bench_bars, trend_params, asof=i)
        if m is None:
            i += 1
            continue
        score, _, _ = ti.trend_score(m, trend_params)

        if not in_pos:
            if score >= p["entry_threshold"]:
                entry_idx = i + 1
                entry_price = _exec_price(bars, entry_idx, p["entry"]) * (1 + cost)
                in_pos = True
            i += 1
            continue

        # 保有中: 決済判定(t の情報で判断、t+1 で執行)
        held = i - entry_idx
        cur_close = bars[i]["close"]
        gross_ret = cur_close / (entry_price / (1 + cost)) - 1
        reason = None
        if gross_ret <= -p["stop_loss_pct"]:
            reason = "stop_loss"
        elif gross_ret >= p["take_profit_pct"]:
            reason = "take_profit"
        elif score < p["exit_threshold"]:
            reason = "trend_break"
        elif held >= p["hold_max_days"]:
            reason = "max_hold"

        if reason:
            exit_idx = i + 1
            exit_price = _exec_price(bars, exit_idx, p["entry"]) * (1 - cost)
            net_ret = exit_price / entry_price - 1
            trades.append({
                "entry_date": bars[entry_idx]["date"],
                "exit_date": bars[exit_idx]["date"],
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "net_return": net_ret,
                "hold_days": exit_idx - entry_idx,
                "exit_reason": reason,
            })
            in_pos = False
        i += 1

    return _split_and_metrics(trades, bars, bench_bars, p)


def _benchmark_buyhold(bench_bars, date_from, date_to):
    seg = [b for b in bench_bars if date_from <= b["date"] <= date_to]
    if len(seg) < 2 or seg[0]["close"] == 0:
        return None
    return seg[-1]["close"] / seg[0]["close"] - 1


def _metrics(trades):
    if not trades:
        return {"trades": 0}
    rets = [t["net_return"] for t in trades]
    wins = [r for r in rets if r > 0]
    losses = [r for r in rets if r <= 0]
    avg = sum(rets) / len(rets)
    std = math.sqrt(sum((r - avg) ** 2 for r in rets) / len(rets)) if len(rets) > 1 else 0.0
    # 取引リターンベースの簡易シャープ(リスクフリー0、年率化なし)
    sharpe = (avg / std) if std > 0 else 0.0
    # エクイティカーブ(複利)と最大DD
    equity, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        equity *= (1 + r)
        peak = max(peak, equity)
        mdd = min(mdd, equity / peak - 1)
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    return {
        "trades": len(trades),
        "win_rate": len(wins) / len(trades),
        "avg_return": avg,
        "avg_win": (sum(wins) / len(wins)) if wins else 0.0,
        "avg_loss": (sum(losses) / len(losses)) if losses else 0.0,
        "total_return": equity - 1,
        "max_drawdown": mdd,
        "sharpe_per_trade": sharpe,
        "avg_hold_days": sum(t["hold_days"] for t in trades) / len(trades),
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
    }


def _split_and_metrics(trades, bars, bench_bars, p):
    train_end = p.get("train_end")
    if train_end:
        train = [t for t in trades if t["entry_date"] <= train_end]
        test = [t for t in trades if t["entry_date"] > train_end]
    else:
        # 期間の前半/後半でざっくり分割
        mid = bars[len(bars) // 2]["date"] if bars else None
        train = [t for t in trades if mid and t["entry_date"] <= mid]
        test = [t for t in trades if mid and t["entry_date"] > mid]
        train_end = mid

    full_from = bars[0]["date"] if bars else ""
    full_to = bars[-1]["date"] if bars else ""
    return {
        "train_end": train_end,
        "all": _metrics(trades),
        "train": _metrics(train),
        "test": _metrics(test),
        "trades": trades,
        "benchmark_buyhold_full": _benchmark_buyhold(bench_bars, full_from, full_to),
        "period": (full_from, full_to),
    }
