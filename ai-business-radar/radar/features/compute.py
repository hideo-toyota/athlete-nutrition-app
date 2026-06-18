"""Pure feature calculations for EDINET DB financials raw.

No file I/O, network, environment variables, or recommendations.
"""
from __future__ import annotations

import math
from datetime import date

from . import registry


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _to_float(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if math.isfinite(v) else None
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s:
            return None
        try:
            f = float(s)
        except ValueError:
            return None
        return f if math.isfinite(f) else None
    return None


def _period_key(row: dict, pos: int):
    year = _to_float(row.get("fiscal_year") or row.get("fiscalYear") or row.get("year"))
    d = row.get("period_end") or row.get("fiscal_year_end") or row.get("fiscalYearEnd")
    ordinal = -1
    if isinstance(d, str):
        try:
            ordinal = date.fromisoformat(d[:10]).toordinal()
        except ValueError:
            ordinal = -1
    return (int(year) if year is not None else -1, ordinal, pos)


def _periods(raw: dict) -> tuple[dict | None, dict | None]:
    rows = raw.get("data")
    if not isinstance(rows, list):
        return None, None
    dict_rows = [r for r in rows if isinstance(r, dict)]
    if not dict_rows:
        return None, None
    ordered = sorted(enumerate(dict_rows), key=lambda kv: _period_key(kv[1], kv[0]))
    current = ordered[-1][1]
    previous = ordered[-2][1] if len(ordered) > 1 else None
    return current, previous


def _period_label(row: dict | None) -> dict:
    if row is None:
        return {}
    label = {}
    for key in ("fiscal_year", "fiscalYear", "year", "period_end", "fiscal_year_end", "fiscalYearEnd"):
        if key in row:
            label[key] = row[key]
    return label


def _resolve(row: dict | None, logical: str):
    if row is None:
        return None, None, "missing_period"
    found = []
    for field in registry.ALIASES[logical]:
        if field in row:
            value = _to_float(row.get(field))
            if value is not None:
                found.append((field, value))
    if not found:
        return None, None, "missing"
    first = found[0][1]
    if any(v != first for _, v in found[1:]):
        fields = ",".join(f for f, _ in found)
        return None, None, f"alias_conflict:{fields}"
    return first, found[0][0], None


def _measured(
    feature_id: str,
    value,
    *,
    source_fields=None,
    source_periods=None,
    hashes=None,
    note=None,
):
    spec = registry.FEATURES[feature_id]
    if value is None:
        status = registry.STATUS_UNKNOWN
    else:
        status = registry.STATUS_CALCULATION
    h = hashes or {}
    return {
        "value": value,
        "status": status,
        "unit": spec["unit"],
        "classification": spec["classification"],
        "formula_id": spec["formula_id"],
        "source_fields": list(source_fields or []),
        "source_periods": list(source_periods or []),
        "raw_hash_normalized": h.get("raw_hash_normalized"),
        "raw_hash_compressed": h.get("raw_hash_compressed"),
        "note": note,
    }


def _unknown(feature_id: str, note: str):
    return _measured(feature_id, None, note=note)


def _ratio(n, d):
    if n is None or d is None or d <= 0:
        return None
    return n / d


def _used(used: dict, period: str, logical: str, field: str | None, value):
    if field is not None:
        used.setdefault(period, {})[logical] = {"field": field, "value": value}


def _restatement_flags(raw: dict) -> list[dict]:
    flags = []
    rows = raw.get("data")
    if not isinstance(rows, list):
        return flags
    needles = ("restatement", "revised", "revision", "correction", "訂正", "修正")
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        for k, v in row.items():
            if any(n in str(k).lower() for n in needles) and v not in (None, "", False):
                flags.append({"row": i, "field": k, "value": v})
    return flags


def compute_financial_features(raw: dict, *, raw_hashes: dict | None = None) -> dict:
    """Return feature dict + source snapshot from an EDINET DB financials raw dict."""
    current, previous = _periods(raw)
    used: dict = {}
    features: dict = {}

    def val(period_name: str, row: dict | None, logical: str):
        value, field, err = _resolve(row, logical)
        _used(used, period_name, logical, field, value)
        return value, field, err

    cur_rev, cur_rev_f, cur_rev_err = val("current", current, "revenue")
    prev_rev, prev_rev_f, prev_rev_err = val("previous", previous, "revenue")
    if cur_rev is not None and prev_rev is not None and prev_rev > 0:
        features["revenue_growth_yoy"] = _measured(
            "revenue_growth_yoy",
            (cur_rev / prev_rev) - 1,
            source_fields=[cur_rev_f, prev_rev_f],
            source_periods=["current", "previous"],
            hashes=raw_hashes,
        )
    else:
        features["revenue_growth_yoy"] = _measured(
            "revenue_growth_yoy", None, hashes=raw_hashes,
            note=cur_rev_err or prev_rev_err or "previous_revenue_non_positive",
        )

    op, op_f, op_err = val("current", current, "operating_income")
    op_margin = _ratio(op, cur_rev)
    features["operating_margin"] = _measured(
        "operating_margin", op_margin,
        source_fields=[f for f in (op_f, cur_rev_f) if f],
        source_periods=["current"],
        hashes=raw_hashes,
        note=None if op_margin is not None else (op_err or cur_rev_err or "revenue_non_positive"),
    )

    ni, ni_f, ni_err = val("current", current, "net_income")
    net_margin = _ratio(ni, cur_rev)
    features["net_margin"] = _measured(
        "net_margin", net_margin,
        source_fields=[f for f in (ni_f, cur_rev_f) if f],
        source_periods=["current"],
        hashes=raw_hashes,
        note=None if net_margin is not None else (ni_err or cur_rev_err or "revenue_non_positive"),
    )

    cur_eq, cur_eq_f, cur_eq_err = val("current", current, "equity")
    prev_eq, prev_eq_f, prev_eq_err = val("previous", previous, "equity")
    avg_eq = ((cur_eq + prev_eq) / 2) if cur_eq is not None and prev_eq is not None else None
    roe = _ratio(ni, avg_eq)
    features["roe_proxy"] = _measured(
        "roe_proxy", roe,
        source_fields=[f for f in (ni_f, cur_eq_f, prev_eq_f) if f],
        source_periods=["current", "previous"],
        hashes=raw_hashes,
        note=None if roe is not None else (ni_err or cur_eq_err or prev_eq_err or "average_equity_non_positive"),
    )

    features["roic_proxy"] = _measured(
        "roic_proxy", None, hashes=raw_hashes,
        note="UNKNOWN_FIXED_PHASE_C_MINIMAL:no_invested_capital_or_tax_assumption",
    )

    ocf, ocf_f, ocf_err = val("current", current, "operating_cash_flow")
    capex, capex_f, capex_err = val("current", current, "capex")
    fcf = None if ocf is None or capex is None else ocf - abs(capex)
    features["fcf_proxy"] = _measured(
        "fcf_proxy", fcf,
        source_fields=[f for f in (ocf_f, capex_f) if f],
        source_periods=["current"],
        hashes=raw_hashes,
        note=None if fcf is not None else (ocf_err or capex_err),
    )

    cash, cash_f, cash_err = val("current", current, "cash")
    debt, debt_f, debt_err = val("current", current, "interest_bearing_debt")
    net_cash = None if cash is None or debt is None else cash - debt
    features["net_cash"] = _measured(
        "net_cash", net_cash,
        source_fields=[f for f in (cash_f, debt_f) if f],
        source_periods=["current"],
        hashes=raw_hashes,
        note=None if net_cash is not None else (cash_err or debt_err),
    )

    assets, assets_f, assets_err = val("current", current, "total_assets")
    equity_ratio = _ratio(cur_eq, assets)
    features["equity_ratio"] = _measured(
        "equity_ratio", equity_ratio,
        source_fields=[f for f in (cur_eq_f, assets_f) if f],
        source_periods=["current"],
        hashes=raw_hashes,
        note=None if equity_ratio is not None else (cur_eq_err or assets_err or "total_assets_non_positive"),
    )

    features["valuation_status"] = _measured(
        "valuation_status", None, hashes=raw_hashes,
        note="UNKNOWN_FIXED_PHASE_C_MINIMAL:no_prices_or_market_cap_dataset",
    )

    return {
        "features": features,
        "source_snapshot": {
            "current_period": _period_label(current),
            "previous_period": _period_label(previous),
            "used_fields": used,
        },
        "restatement_flags": _restatement_flags(raw),
    }
