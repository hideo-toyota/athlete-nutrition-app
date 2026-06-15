"""target-check の計算ロジック(純計算・ネット無し / TARGET_CHECK_SPEC 準拠)。

目標倍率の「必要年率・税引後の必要倍率・DCA込みの必要リターン・コア/サテライト混合の
到達可能性・破綻ライン」を算出する。**銘柄を扱わない・推奨しない・予測しない。**
結論は「達成可能/不能」でなく「必要条件 / 破綻条件」。
"""
from __future__ import annotations

import math

DEFAULT_TAX_RATE = 0.20315  # 上場株式 譲渡益(所得税+住民税+復興特別)


def _finite_pos(v, name, allow_zero=False):
    if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
        raise SystemExit(f"{name} が有限の数値ではありません: {v!r}")
    if v < 0 or (v == 0 and not allow_zero):
        raise SystemExit(f"{name} は正の数で指定してください: {v}")
    return float(v)


def required_cagr(multiple: float, years: float) -> float:
    return multiple ** (1.0 / years) - 1.0


def gross_multiple_after_tax(net_multiple: float, taxable_frac: float, tax_rate: float) -> float:
    """税引後 net_multiple 倍に必要な“税前”倍率。

    導出: 一律 g 倍成長で、課税分は利益(g-1)に tax、NISA分は非課税 →
    f*(1+(g-1)(1-t)) + (1-f)*g = M を g で解くと g = (M - f*t)/(1 - f*t)。
    f=1(全課税)→ (M-t)/(1-t)、f=0(全NISA)→ M。
    """
    f, t = taxable_frac, tax_rate
    denom = 1.0 - f * t
    if denom <= 0:
        raise SystemExit("tax 設定が不正(1 - taxable_frac*tax_rate <= 0)")
    return (net_multiple - f * t) / denom


def _fv(initial: float, monthly: float, annual_r: float, years: float) -> float:
    """現資産 + 毎月積立 の将来価値(年率 annual_r、積立は月複利)。"""
    g = (1.0 + annual_r) ** years
    m = (1.0 + annual_r) ** (1.0 / 12.0) - 1.0
    n = 12.0 * years
    if abs(m) < 1e-12:
        annuity = monthly * n
    else:
        annuity = monthly * (((1.0 + m) ** n - 1.0) / m)
    return initial * g + annuity


def solve_required_rate(initial: float, monthly: float, years: float, target_value: float):
    """現資産+積立で target_value(税前)に到達する年率 r を二分法で解く。範囲外は None。"""
    lo, hi = -0.99, 10.0
    if _fv(initial, monthly, lo, years) >= target_value:
        return lo  # 積立だけでほぼ到達(必要リターンは極小)
    if _fv(initial, monthly, hi, years) < target_value:
        return None  # 1000%/年でも届かない
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if _fv(initial, monthly, mid, years) >= target_value:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def recovery_needed(drawdown_pct: float) -> float:
    """drawdown_pct(例 50 = -50%)からの回復に必要な上昇率(%)。"""
    d = drawdown_pct / 100.0
    if d >= 1.0:
        return float("inf")
    return (1.0 / (1.0 - d) - 1.0) * 100.0


def compute(multiple, years, *, initial, monthly=0.0, taxable_frac=1.0,
            tax_rate=DEFAULT_TAX_RATE, core_w=0.9, sat_w=0.1, sat_cap_pct=10.0,
            leverage=1.0, max_dd_pct=None) -> dict:
    # --- 入力検証(黙殺しない) ---
    multiple = _finite_pos(multiple, "multiple")
    if multiple <= 1.0:
        raise SystemExit("multiple は 1 より大きい目標倍率を指定してください(例 10)")
    years = _finite_pos(years, "years")
    initial = _finite_pos(initial, "initial")
    monthly = _finite_pos(monthly, "monthly", allow_zero=True)
    leverage = _finite_pos(leverage, "leverage")
    if not (0.0 <= taxable_frac <= 1.0):
        raise SystemExit(f"taxable_frac は 0〜1 で指定してください: {taxable_frac}")
    if not (0.0 <= tax_rate < 1.0):
        raise SystemExit(f"tax_rate は 0〜1 未満で指定してください: {tax_rate}")
    if max_dd_pct is not None:
        max_dd_pct = _finite_pos(max_dd_pct, "max_dd_pct", allow_zero=True)

    # --- 必要リターン ---
    cagr_pretax = required_cagr(multiple, years)
    gross_mult = gross_multiple_after_tax(multiple, taxable_frac, tax_rate)
    cagr_posttax = required_cagr(gross_mult, years)

    # --- DCA 込み(税前 gross 目標に到達する必要年率) ---
    gross_target_value = gross_mult * initial
    r_no_contrib = required_cagr(gross_mult, years)            # 現資産だけ
    r_with_contrib = solve_required_rate(initial, monthly, years, gross_target_value)

    # --- コア/サテライト 混合の到達可能性(中核) ---
    blend_examples = []
    for sat_mult in (5.0, 10.0, 20.0):
        for core_mult, label in ((1.0, "コア横ばい"),):
            total = core_w * core_mult + sat_w * sat_mult
            blend_examples.append({"sat_mult": sat_mult, "core_mult": core_mult,
                                   "core_label": label, "total_mult": total})
    # 全体を multiple 倍にするのにコアが必要とする倍率(sat を上限到達と仮定)
    sat_assumed = 10.0
    core_needed = (multiple - sat_w * sat_assumed) / core_w if core_w > 0 else None

    # --- 破綻・回復 ---
    sat_max_loss_pct = sat_w * 100.0                 # サテライト全損=総資産のこの%
    leverage_ruin_drop_pct = (1.0 / leverage) * 100.0 if leverage > 1.0 else None
    recovery = {d: recovery_needed(d) for d in (20, 30, 50, 70)}
    max_dd_recovery = recovery_needed(max_dd_pct) if max_dd_pct else None

    return {
        "inputs": {"multiple": multiple, "years": years, "initial": initial,
                   "monthly": monthly, "taxable_frac": taxable_frac, "tax_rate": tax_rate,
                   "core_w": core_w, "sat_w": sat_w, "sat_cap_pct": sat_cap_pct,
                   "leverage": leverage, "max_dd_pct": max_dd_pct},
        "cagr_pretax": cagr_pretax,
        "gross_multiple_posttax": gross_mult,
        "cagr_posttax": cagr_posttax,
        "r_no_contrib": r_no_contrib,
        "r_with_contrib": r_with_contrib,
        "blend_examples": blend_examples,
        "core_needed_for_target": core_needed,
        "sat_assumed_for_core_calc": sat_assumed,
        "sat_max_loss_pct": sat_max_loss_pct,
        "leverage_ruin_drop_pct": leverage_ruin_drop_pct,
        "recovery": recovery,
        "max_dd_recovery": max_dd_recovery,
    }
