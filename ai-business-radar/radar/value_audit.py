"""value-audit の純計算(純粋・決定論・I/O無し / EARNINGS_CYCLE_VALUE_AUDIT_SPEC 準拠)。

決算 to 決算の割安“仮説”検証のための数理だけを置く。**銘柄を推奨しない・予測しない。**
- Measured: status 付きの値(UNKNOWN は value=None。0/false にしない)。
- evaluate_condition: 構造化条件(operator 真理表)の機械判定。
- raw_return / cycle_days / annualize: サイクルのリターン数理(範囲外は年率換算を UNKNOWN)。
- aggregate: 較正の集計(分母は確定 status のみ。UNKNOWN を負け/不一致に数えない)。
"""
from __future__ import annotations

import math

# --- CLAIMS 分類(status) ---
FACT = "FACT"
CALCULATION = "CALCULATION"
INFERENCE = "INFERENCE"
ASSUMPTION = "ASSUMPTION"
UNKNOWN = "UNKNOWN"
_CONFIRMED = (FACT, CALCULATION)  # 集計の分母に入れてよい status

ALLOWED_OPERATORS = (">=", ">", "<=", "<", "==", "in_range", "out_of_range")


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def measured(value, status, unit=None, note=None) -> dict:
    """status 付きの値を作る。UNKNOWN のとき value は必ず None(0/false にしない)。"""
    if status == UNKNOWN:
        value = None
    return {"value": value, "status": status, "unit": unit, "note": note}


def unknown(unit=None, note=None) -> dict:
    return measured(None, UNKNOWN, unit=unit, note=note)


def _as_measured(x) -> dict:
    """Measured dict か裸の数値を Measured に正規化(裸数値は ASSUMPTION 既定=手入力前提)。"""
    if isinstance(x, dict) and "status" in x:
        return x
    if _finite(x):
        return measured(float(x), ASSUMPTION)
    return unknown()


# ---------------------------------------------------------------------------
# operator 真理表(SPEC §2.6.1)
# ---------------------------------------------------------------------------
def _check_threshold_type(operator: str, threshold) -> None:
    """threshold の型が operator と整合しなければ ValueError(呼び出し側で停止に変換)。"""
    if operator in ("in_range", "out_of_range"):
        if (not isinstance(threshold, (list, tuple)) or len(threshold) != 2
                or not all(_finite(t) for t in threshold)):
            raise ValueError(f"{operator} の threshold は [lo, hi] の有限数2要素で指定してください: {threshold!r}")
        lo, hi = threshold
        if lo > hi:
            raise ValueError(f"{operator} の threshold は lo <= hi: {threshold!r}")
    else:
        if not _finite(threshold):
            raise ValueError(f"{operator} の threshold は有限の数値で指定してください: {threshold!r}")


def evaluate_condition(cond: dict, actual) -> bool | None:
    """構造化条件 cond を actual(Measured または数値)で判定。

    返り値:
      - True/False : 判定できた
      - None       : 判定対象外(qualitative_only / actual が UNKNOWN・非数値)→ 集計分母から除外
    真理表:
      >=: a >= th - tol   >: a > th - tol   <=: a <= th + tol   <: a < th + tol
      ==: |a - th| <= tol
      in_range:  lo - tol <= a <= hi + tol(境界含む)
      out_of_range: a < lo - tol or a > hi + tol
    tolerance 未指定は 0.0。threshold 型不整合は ValueError。actual 非数値/nan/inf/UNKNOWN は None(0にしない)。
    """
    if not isinstance(cond, dict):
        raise ValueError("condition は object である必要があります")
    if cond.get("qualitative_only") is True:
        return None
    operator = cond.get("operator")
    if operator not in ALLOWED_OPERATORS:
        raise ValueError(f"operator が不正: {operator!r}(許容: {ALLOWED_OPERATORS})")
    threshold = cond.get("threshold")
    _check_threshold_type(operator, threshold)
    tol = cond.get("tolerance", 0.0)
    if tol is None:
        tol = 0.0
    if not _finite(tol) or tol < 0:
        raise ValueError(f"tolerance は非負の有限数で指定してください: {tol!r}")

    m = _as_measured(actual)
    if m["status"] == UNKNOWN:
        return None
    a = m["value"]
    if not _finite(a):
        return None  # 非数値/nan/inf は UNKNOWN 扱い(0にしない)

    if operator == ">=":
        return a >= threshold - tol
    if operator == ">":
        return a > threshold - tol
    if operator == "<=":
        return a <= threshold + tol
    if operator == "<":
        return a < threshold + tol
    if operator == "==":
        return abs(a - threshold) <= tol
    lo, hi = threshold
    if operator == "in_range":
        return (a >= lo - tol) and (a <= hi + tol)
    # out_of_range
    return (a < lo - tol) or (a > hi + tol)


# ---------------------------------------------------------------------------
# サイクルのリターン数理
# ---------------------------------------------------------------------------
def raw_return(entry_price: float, exit_price: float) -> float:
    """素のリターン exit/entry - 1。entry は正の有限数。"""
    if not _finite(entry_price) or entry_price <= 0:
        raise ValueError(f"entry_price は正の有限数で指定してください: {entry_price!r}")
    if not _finite(exit_price) or exit_price < 0:
        raise ValueError(f"exit_price は非負の有限数で指定してください: {exit_price!r}")
    return exit_price / entry_price - 1.0


def cycle_days(start_days: int, end_days: int) -> int:
    """サイクル日数(end - start)。負なら ValueError。引数は ordinal(date.toordinal())。"""
    if not isinstance(start_days, int) or not isinstance(end_days, int):
        raise ValueError("cycle_days は ordinal(int)で渡してください")
    d = end_days - start_days
    if d < 0:
        raise ValueError(f"サイクル終端が起点より前です: start={start_days} end={end_days}")
    return d


def annualize(raw: float, days: int, cfg: dict) -> dict:
    """素のリターンを年率換算(Measured)。days が [min,max] 外なら UNKNOWN(警告)で返す。"""
    if not _finite(raw):
        return unknown(unit="%", note="raw_return が数値でない")
    min_d = cfg.get("min_cycle_days", 45)
    max_d = cfg.get("max_cycle_days", 200)
    base = cfg.get("annualization_day_base", 365)
    if not isinstance(days, int) or days <= 0:
        return unknown(unit="%", note=f"cycle_days 不正: {days!r}")
    if days < min_d or days > max_d:
        return unknown(unit="%",
                       note=f"cycle_days={days} が [{min_d},{max_d}] 外のため年率換算は除外(短期/長期の外れ値)")
    ann = (1.0 + raw) ** (base / days) - 1.0
    return measured(ann, CALCULATION, unit="%")


def vs_target(annualized: dict, hurdle_frac: float) -> dict:
    """年率換算が確定値のときのみ、ハードル超過を判定(Measured)。"""
    if not isinstance(annualized, dict) or annualized.get("status") != CALCULATION:
        return unknown(note="年率換算が UNKNOWN のため対ハードル判定は保留")
    return measured(bool(annualized["value"] >= hurdle_frac), CALCULATION)


# ---------------------------------------------------------------------------
# 較正の集計(分母は確定 status のみ・UNKNOWN を負け/不一致に数えない)
# ---------------------------------------------------------------------------
def _rate(num: int, den: int):
    return (num / den) if den else None


def aggregate(outcomes: list[dict], cfg: dict) -> dict:
    """採点済み outcome 群を集計。Phase A は対DCA を UNKNOWN(分母0)で率を出さない。"""
    n = len(outcomes)
    # 反証発火
    fired = [o for o in outcomes if o.get("falsification_triggered")]
    total_triggers = sum(len(o.get("falsification_triggered") or []) for o in outcomes)
    # checklist 一致率(SPEC §2.0/§4.1: 分母は actual.status が FACT/CALCULATION のもののみ)。
    # ASSUMPTION(手入力・Phase A)は正式分母から除外し、別枠の「参考一致率」に集計(混ぜない)。
    # UNKNOWN/qualitative は matched=None として両方の分母から除外(負け/不一致に数えない)。
    cl_den = cl_hit = 0          # 正式(FACT/CALCULATION)
    ref_den = ref_hit = 0        # 参考(ASSUMPTION依存)
    for o in outcomes:
        for item in (o.get("checklist_result") or []):
            if item.get("qualitative_only") or item.get("matched") is None:
                continue
            st = (item.get("actual") or {}).get("status")
            if st in _CONFIRMED:
                cl_den += 1
                if item.get("matched") is True:
                    cl_hit += 1
            elif st == ASSUMPTION:
                ref_den += 1
                if item.get("matched") is True:
                    ref_hit += 1
    # 対10% hit(annualized が確定したものだけ)
    h10_den = h10_hit = 0
    n_ann_unknown = 0
    for o in outcomes:
        v = o.get("vs_target_10pct") or {}
        if v.get("status") == CALCULATION:
            h10_den += 1
            if v.get("value") is True:
                h10_hit += 1
        ann = o.get("annualized_return") or {}
        if ann.get("status") == UNKNOWN:
            n_ann_unknown += 1
    # 対DCA hit(benchmark が確定したものだけ。Phase A は 0=率を出さない)
    dca_den = dca_hit = 0
    for o in outcomes:
        bd = o.get("beat_dca") or {}
        if bd.get("status") == CALCULATION:
            dca_den += 1
            if bd.get("value") is True:
                dca_hit += 1
    # リスク(最大DD の確定値のみ)
    dd_known = [o["max_drawdown_pct"]["value"] for o in outcomes
                if (o.get("max_drawdown_pct") or {}).get("status") in _CONFIRMED]

    return {
        "n_scored": n,
        "n_annualized_unknown": n_ann_unknown,
        "falsification_outcomes": len(fired),
        "falsification_total_triggers": total_triggers,
        "checklist_match_rate": _rate(cl_hit, cl_den), "checklist_den": cl_den,
        "checklist_ref_rate": _rate(ref_hit, ref_den), "checklist_ref_den": ref_den,
        "hit_10pct": _rate(h10_hit, h10_den), "hit_10pct_den": h10_den,
        "hit_dca": _rate(dca_hit, dca_den), "hit_dca_den": dca_den,  # Phase A: den=0 → None
        "max_dd_known": dd_known,
    }
