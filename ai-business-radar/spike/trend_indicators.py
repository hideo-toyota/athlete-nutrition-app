"""上昇トレンド指標・スコア・ラベル(標準ライブラリのみ)。

すべての計算は `asof` 番目のバーまでのデータだけを使うように書かれており、
バックテストでも未来データを参照しません(look-ahead bias の回避)。
"""
from __future__ import annotations

from datetime import date

# 既定パラメータ(equity_watchlist.json の trend_params で上書き可)
DEFAULTS = {
    "ma_windows": [20, 60, 120],
    "slope_window": 10,          # MA の傾きを測る日数
    "high_windows": [20, 60],    # n日高値からの距離
    "return_windows": [20, 60, 120],
    "rel_window": 60,            # ベンチマーク相対リターンの窓
    "vol_avg_window": 20,
    "atr_window": 14,
    "range_window": 20,
    "dd_window": 120,            # 最大ドローダウンの窓
    "overheat_pct": 0.15,        # 20MAからの上方乖離がこれ超で過熱
    "overheat_strong_pct": 0.22,
    "spike_window": 5,
    "spike_pct": 0.25,           # 直近spike_windowの累積上昇がこれ超で急騰
    "thin_volume_ratio": 0.7,
    "vol_confirm_ratio": 1.2,
    "min_turnover": 100_000_000, # 流動性十分とみなす売買代金20日平均(円)
    "breakdown_day_pct": -0.08,  # 下落日に大きく崩れるとみなす単日下落
    "earnings_window_days": 7,
    "limit_move_pct": 0.17,      # ストップ高/安の代理判定(単日変化)
    "strong_score": 70,
    "candidate_score": 58,
    "downtrend_score": 30,
}


# ---------------------------------------------------------------------------
# 基礎計算
# ---------------------------------------------------------------------------
def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def sma(values, n, i):
    """values[i] を末尾とする n 本の単純移動平均。足りなければ None。"""
    if i + 1 < n:
        return None
    return _mean(values[i - n + 1:i + 1])


def slope_pct(values, n, i, window):
    """i 時点の n日MA の、window 日前比の変化率(傾きの代理)。"""
    cur = sma(values, n, i)
    prev = sma(values, n, i - window)
    if cur is None or prev is None or prev == 0:
        return None
    return cur / prev - 1


def return_pct(closes, n, i):
    if i - n < 0 or closes[i - n] == 0:
        return None
    return closes[i] / closes[i - n] - 1


def max_in_window(values, n, i):
    if i + 1 < 1:
        return None
    start = max(0, i - n + 1)
    return max(values[start:i + 1])


def max_drawdown(closes, n, i):
    start = max(0, i - n + 1)
    window = closes[start:i + 1]
    if not window:
        return None
    peak = window[0]
    mdd = 0.0
    for v in window:
        peak = max(peak, v)
        if peak > 0:
            mdd = min(mdd, v / peak - 1)
    return mdd


def atr(bars, n, i):
    if i + 1 < n + 1:
        return None
    trs = []
    for j in range(i - n + 1, i + 1):
        h, l, pc = bars[j]["high"], bars[j]["low"], bars[j - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return _mean(trs)


def range_pct(bars, n, i):
    if i + 1 < n:
        return None
    vals = [(bars[j]["high"] - bars[j]["low"]) / bars[j]["close"]
            for j in range(i - n + 1, i + 1) if bars[j]["close"]]
    return _mean(vals)


def _bench_return(bench_by_date, dates, n, i):
    """ベンチマークの i 時点 vs n日前のリターン(同じ日付で突き合わせ)。"""
    if i - n < 0:
        return None
    d_now, d_prev = dates[i], dates[i - n]
    c_now = _bench_close_on_or_before(bench_by_date, d_now)
    c_prev = _bench_close_on_or_before(bench_by_date, d_prev)
    if c_now is None or c_prev is None or c_prev == 0:
        return None
    return c_now / c_prev - 1


def _bench_close_on_or_before(bench_by_date, d):
    if d in bench_by_date:
        return bench_by_date[d]
    # その日が無ければ直近過去を探す(軽量に走査)
    best = None
    for bd, bc in bench_by_date.items():
        if bd <= d and (best is None or bd > best[0]):
            best = (bd, bc)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# 指標一括計算
# ---------------------------------------------------------------------------
def compute_indicators(bars, bench_bars, params, asof=None):
    p = {**DEFAULTS, **(params or {})}
    if not bars:
        return None
    i = len(bars) - 1 if asof is None else asof
    need = max(p["ma_windows"]) + p["slope_window"]
    if i < need:
        return None

    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    vols = [b["volume"] for b in bars]
    dates = [b["date"] for b in bars]
    bench_by_date = {b["date"]: b["close"] for b in bench_bars}

    w = p["ma_windows"]
    ma = {n: sma(closes, n, i) for n in w}
    slope = {n: slope_pct(closes, n, i, p["slope_window"]) for n in (w[0], w[1])}
    close = closes[i]

    m = {
        "date": dates[i],
        "close": close,
        "ma": ma,
        "slope": slope,
        "above_ma": {n: (ma[n] is not None and close > ma[n]) for n in w},
    }

    # n日高値からの距離
    m["dist_high"] = {}
    for n in p["high_windows"]:
        hh = max_in_window(highs, n, i)
        m["dist_high"][n] = (close / hh - 1) if hh else None

    # 年初来高値
    year = int(dates[i][:4])
    ytd_high = max((highs[j] for j in range(i + 1) if int(dates[j][:4]) == year),
                   default=None)
    m["dist_ytd_high"] = (close / ytd_high - 1) if ytd_high else None

    # リターン
    m["returns"] = {n: return_pct(closes, n, i) for n in p["return_windows"]}

    # ベンチ相対(rel_window)
    rw = p["rel_window"]
    stock_ret = return_pct(closes, rw, i)
    bench_ret = _bench_return(bench_by_date, dates, rw, i)
    m["bench_return"] = bench_ret
    m["stock_return_relwin"] = stock_ret
    m["rel_return"] = (stock_ret - bench_ret) if (stock_ret is not None and bench_ret is not None) else None

    # 出来高・流動性
    avg_vol = _mean(vols[i - p["vol_avg_window"] + 1:i + 1]) if i + 1 >= p["vol_avg_window"] else None
    m["volume_ratio"] = (vols[i] / avg_vol) if avg_vol else None
    turn = [closes[j] * vols[j] for j in range(i - p["vol_avg_window"] + 1, i + 1)] if i + 1 >= p["vol_avg_window"] else []
    m["turnover_20"] = _mean(turn) if turn else None

    # ボラ・DD
    m["atr"] = atr(bars, p["atr_window"], i)
    m["atr_pct"] = (m["atr"] / close) if (m["atr"] and close) else None
    m["range_pct"] = range_pct(bars, p["range_window"], i)
    m["max_drawdown"] = max_drawdown(closes, p["dd_window"], i)

    # 過熱・急騰
    dist20 = ((close - ma[w[0]]) / ma[w[0]]) if ma[w[0]] else None
    m["dist_from_ma20"] = dist20
    m["overheated"] = bool(dist20 is not None and dist20 > p["overheat_pct"])
    m["overheated_strong"] = bool(dist20 is not None and dist20 > p["overheat_strong_pct"])
    sw = p["spike_window"]
    if i - sw >= 0:
        spike_ret = closes[i] / closes[i - sw] - 1
        down_days = sum(1 for j in range(i - sw + 1, i + 1) if closes[j] < closes[j - 1])
        m["spike_no_pullback"] = bool(spike_ret > p["spike_pct"] and down_days == 0)
    else:
        m["spike_no_pullback"] = False

    # 下落日の崩れ
    worst = min((closes[j] / closes[j - 1] - 1) for j in range(max(1, i - 19), i + 1))
    m["worst_day_return"] = worst
    m["big_breakdown"] = bool(worst < p["breakdown_day_pct"])

    # ストップ高/安(代理)
    day_ret = closes[i] / closes[i - 1] - 1 if i >= 1 else 0
    m["limit_up_proxy"] = bool(day_ret >= p["limit_move_pct"])
    m["limit_down_proxy"] = bool(day_ret <= -p["limit_move_pct"])

    # 決算跨ぎ
    m["days_to_earnings"] = None
    m["earnings_crossing_risk"] = False
    return m


def attach_earnings(m, next_earnings_date):
    if not next_earnings_date:
        return
    try:
        ed = date.fromisoformat(next_earnings_date)
        asof = date.fromisoformat(m["date"])
        days = (ed - asof).days
        m["days_to_earnings"] = days
        m["earnings_crossing_risk"] = 0 <= days <= DEFAULTS["earnings_window_days"]
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# スコア(0-100)
# ---------------------------------------------------------------------------
def trend_score(m, params=None):
    p = {**DEFAULTS, **(params or {})}
    w = p["ma_windows"]
    adds, subs = [], []

    def add(cond, pts, label):
        if cond:
            adds.append((label, pts))

    def sub(cond, pts, label):
        if cond:
            subs.append((label, -pts))

    ma = m["ma"]
    perfect = (ma[w[0]] and ma[w[1]] and ma[w[2]]
               and ma[w[0]] > ma[w[1]] > ma[w[2]])

    add(m["above_ma"][w[0]], 8, "終値が20日線の上")
    add(m["above_ma"][w[1]], 8, "終値が60日線の上")
    add(m["above_ma"][w[2]], 8, "終値が120日線の上")
    add(perfect, 12, "20>60>120日線の並び(パーフェクトオーダー)")
    add((m["slope"][w[0]] or 0) > 0, 8, "20日線が上向き")
    add((m["slope"][w[1]] or 0) > 0, 8, "60日線が上向き")
    add((m["returns"][w[1]] or 0) > 0, 8, "60日リターンがプラス")
    add((m["rel_return"] or 0) > 0, 12, "ベンチマーク比で強い")
    add((m["volume_ratio"] or 0) >= p["vol_confirm_ratio"] and (m["returns"][w[0]] or 0) > 0,
        8, "出来高を伴って上昇")
    add((m["turnover_20"] or 0) >= p["min_turnover"], 8, "流動性が十分")
    add(m["dist_high"].get(w[1]) is not None and m["dist_high"][w[1]] >= -0.05,
        12, "60日高値圏を維持")

    sub(m["overheated"], 12, "20日線から離れすぎて過熱")
    sub((m["volume_ratio"] or 1) < p["thin_volume_ratio"], 8, "出来高が細い")
    sub(m["spike_no_pullback"], 10, "急騰直後で押し目がない")
    sub(m["earnings_crossing_risk"], 10, "決算直前でリスクが高い")
    sub((m["max_drawdown"] or 0) < -0.30, 10, "最大ドローダウンが大きい")
    sub((m["rel_return"] or 0) < 0, 12, "ベンチマークより弱い")
    sub(m["big_breakdown"], 8, "下落日に大きく崩れる")

    raw = sum(p for _, p in adds) + sum(p for _, p in subs)
    score = max(0, min(100, round(raw)))
    return score, adds, subs


# ---------------------------------------------------------------------------
# ラベル
# ---------------------------------------------------------------------------
def trend_label(m, score, params=None):
    p = {**DEFAULTS, **(params or {})}
    w = p["ma_windows"]
    ma = m["ma"]
    above20 = m["above_ma"][w[0]]
    above60 = m["above_ma"][w[1]]
    above120 = m["above_ma"][w[2]]
    up20 = (m["slope"][w[0]] or 0) > 0
    up60 = (m["slope"][w[1]] or 0) > 0
    perfect = ma[w[0]] and ma[w[1]] and ma[w[2]] and ma[w[0]] > ma[w[1]] > ma[w[2]]
    downtrend_struct = (not above60) and (m["slope"][w[1]] or 0) < 0

    if m["overheated_strong"] or m["spike_no_pullback"]:
        return "過熱注意"
    if downtrend_struct or score < p["downtrend_score"]:
        return "下落トレンド"
    if perfect and above120 and up20 and up60 and score >= p["strong_score"]:
        return "強い上昇トレンド"
    if above60 and up60 and score >= p["candidate_score"]:
        return "上昇トレンド候補"
    if above60 and up60 and not above20:
        return "押し目監視"
    return "レンジ"
