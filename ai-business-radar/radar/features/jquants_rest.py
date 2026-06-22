"""Build J-Quants derived features from REST API payloads (no network here).

The radar pipeline consumes the `jquants_equity_v1` derived feature set. The
J-Quants *bulk* CSV builder (jquants_bulk.py) is one producer; this module is a
second producer that accepts already-fetched *REST* API payloads (the shape
`scripts/jquants_client.py` returns) and writes the identical derived schema, so
research-queue / evidence / llm-brief / daily-update work unchanged.

This module performs NO network I/O. `radar.sources.jquants_rest_client` fetches;
`fetch_and_build` wires a client in. Tests inject payloads directly.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .jquants_bulk import (
    FEATURE_REGISTRY_VERSION,
    FEATURE_SET,
    NORMALIZATION_VERSION,
    PROVIDER,
    SCHEMA_VERSION,
    _date_or_none,
    _float_or_none,
    _measured,
    _output_dir,
    _market_cap,
    _per_pbr,
    _financial_period_label,
    _ratio,
    _return,
    _valid_asof,
)

# REST statement field aliases (J-Quants /fins/statements long names).
_REST_SALES = ("NetSales", "Sales", "OperatingRevenues", "OrdinaryRevenues", "Revenue")
_REST_OP = ("OperatingProfit", "OperatingIncome")
_REST_NP = ("Profit", "ProfitAttributableToOwnersOfParent", "NetIncome")
_REST_EQ = ("Equity", "NetAssets")
_REST_TA = ("TotalAssets",)
_REST_EPS = ("EarningsPerShare",)
_REST_BPS = ("BookValuePerShare",)
_REST_SHARES = (
    "NumberOfIssuedAndOutstandingSharesAtTheEndOfFiscalYearIncludingTreasuryStock",
    "NumberOfIssuedAndOutstandingShares",
)


def _pick(row: dict, keys: tuple[str, ...]):
    for k in keys:
        v = _float_or_none(row.get(k))
        if v is not None:
            return v, k
    return None, None


def _price_points(daily_quotes: list[dict], asof_date: date):
    points = []
    for row in daily_quotes or []:
        d = _date_or_none(row.get("Date"))
        if d is None or d > asof_date:
            continue
        close = _float_or_none(row.get("AdjustmentClose"))
        if close is None:
            close = _float_or_none(row.get("Close"))
        vol = _float_or_none(row.get("AdjustmentVolume"))
        if vol is None:
            vol = _float_or_none(row.get("Volume"))
        if close is not None and close > 0:
            points.append((d, close, vol))
    points.sort(key=lambda x: x[0])
    return points


def _rest_financials(statements: list[dict], asof_date: date) -> dict:
    rows = []
    for row in statements or []:
        if str(row.get("TypeOfCurrentPeriod", "")) != "FY":
            continue
        disc = _date_or_none(row.get("DisclosedDate"))
        if disc is None or disc > asof_date:
            continue
        rows.append(row)
    rows.sort(key=lambda r: (str(r.get("CurrentPeriodEndDate", "")), str(r.get("DisclosedDate", ""))))
    cur = rows[-1] if rows else None
    prev = rows[-2] if len(rows) >= 2 else None
    if cur is None:
        return {"latest_disclosure_date": None, "sales_growth_yoy": None, "operating_margin": None,
                "net_margin": None, "roe_proxy": None, "equity_ratio": None, "eps": None, "bps": None,
                "eps_source": None, "bps_source": None, "shares": None, "shares_source": None,
                "net_profit": None, "equity": None, "current_period": None,
                "previous_period": None, "used_fields": {}}
    sales, sales_source = _pick(cur, _REST_SALES)
    prev_sales, prev_sales_source = _pick(prev, _REST_SALES) if prev else (None, None)
    op, op_source = _pick(cur, _REST_OP)
    np, np_source = _pick(cur, _REST_NP)
    eq, eq_source = _pick(cur, _REST_EQ)
    prev_eq, prev_eq_source = _pick(prev, _REST_EQ) if prev else (None, None)
    ta, ta_source = _pick(cur, _REST_TA)
    avg_eq = ((eq + prev_eq) / 2) if eq is not None and prev_eq is not None else None
    eps, eps_source = _pick(cur, _REST_EPS)
    bps, bps_source = _pick(cur, _REST_BPS)
    shares, shares_source = _pick(cur, _REST_SHARES)
    used_fields = {
        "current": {
            "sales": {"field": sales_source, "value": sales},
            "operating_income": {"field": op_source, "value": op},
            "net_income": {"field": np_source, "value": np},
            "equity": {"field": eq_source, "value": eq},
            "total_assets": {"field": ta_source, "value": ta},
            "eps": {"field": eps_source, "value": eps},
            "bps": {"field": bps_source, "value": bps},
            "shares": {"field": shares_source, "value": shares},
        },
        "previous": {
            "sales": {"field": prev_sales_source, "value": prev_sales},
            "equity": {"field": prev_eq_source, "value": prev_eq},
        },
    }
    return {
        "latest_disclosure_date": cur.get("DisclosedDate"),
        "sales_growth_yoy": (sales / prev_sales - 1) if sales is not None and prev_sales not in (None, 0) and prev_sales > 0 else None,
        "operating_margin": _ratio(op, sales),
        "net_margin": _ratio(np, sales),
        "roe_proxy": _ratio(np, avg_eq),
        "equity_ratio": _ratio(eq, ta),
        "eps": eps, "bps": bps, "eps_source": eps_source, "bps_source": bps_source,
        "shares": shares, "shares_source": shares_source, "net_profit": np, "equity": eq,
        "current_period": _financial_period_label({
            "CurPerEn": cur.get("CurrentPeriodEndDate"),
            "DiscDate": cur.get("DisclosedDate"),
            "DiscTime": cur.get("DisclosedTime"),
            "DiscNo": cur.get("DisclosureNumber"),
            "CurPerType": cur.get("TypeOfCurrentPeriod"),
            "DocType": cur.get("TypeOfDocument"),
        }),
        "previous_period": _financial_period_label({
            "CurPerEn": prev.get("CurrentPeriodEndDate"),
            "DiscDate": prev.get("DisclosedDate"),
            "DiscTime": prev.get("DisclosedTime"),
            "DiscNo": prev.get("DisclosureNumber"),
            "CurPerType": prev.get("TypeOfCurrentPeriod"),
            "DocType": prev.get("TypeOfDocument"),
        }) if prev else None,
        "used_fields": used_fields,
    }


def _normalize_code(code: str) -> str:
    code = str(code).strip().upper()
    return code + "0" if len(code) == 4 else code


def _entity(listed_info: dict) -> dict:
    info = (listed_info or {}).get("info") if isinstance(listed_info, dict) else None
    row = (info or [{}])[-1] if info else {}
    return {
        "company_name": row.get("CompanyName") or row.get("CompanyNameEnglish") or "",
        "market": row.get("MarketCodeName") or "",
        "sector33": row.get("Sector33CodeName") or "",
    }


def build_jquants_features_from_payloads(
    *, payloads: dict, asof: str, derived_root: Path | None = None, clock=None,
) -> dict:
    """payloads: {code: {"daily_quotes":[...], "listed_info":{...}, "statements":[...]}}."""
    asof = _valid_asof(asof)
    asof_date = date.fromisoformat(asof)
    out_dir = _output_dir(derived_root, asof)
    generated = clock() if clock else datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    generated_at = generated.astimezone(timezone.utc).isoformat(timespec="seconds")

    features_path = out_dir / "features.jsonl"
    manifest_path = out_dir / "manifest.json"

    per_vals, pbr_vals = [], []
    price_covered = summary_covered = valuation_covered = 0
    shares_covered = market_cap_covered = 0
    latest_price_date = None
    alias_hits = {"eps": Counter(), "bps": Counter(), "shares": Counter(),
                  "per_method": Counter(), "pbr_method": Counter()}
    uncovered = Counter()

    codes = sorted(_normalize_code(c) for c in payloads)
    with features_path.open("w", encoding="utf-8") as fh:
        for raw_code in sorted(payloads):
            code = _normalize_code(raw_code)
            p = payloads[raw_code] or {}
            dq = (p.get("daily_quotes") or {}).get("daily_quotes") if isinstance(p.get("daily_quotes"), dict) else p.get("daily_quotes")
            statements = (p.get("statements") or {}).get("statements") if isinstance(p.get("statements"), dict) else p.get("statements")
            points = _price_points(dq or [], asof_date)
            latest = points[-1] if points else None
            if latest:
                price_covered += 1
                latest_price_date = latest[0] if latest_price_date is None or latest[0] > latest_price_date else latest_price_date
            f = _rest_financials(statements or [], asof_date)
            if f["latest_disclosure_date"]:
                summary_covered += 1
            close_val = latest[1] if latest else None
            per, pbr, per_method, pbr_method = _per_pbr(close_val, f)
            market_cap = _market_cap(close_val, f.get("shares"))
            if f.get("eps_source") and f.get("eps") is not None:
                alias_hits["eps"][f["eps_source"]] += 1
            if f.get("bps_source") and f.get("bps") is not None:
                alias_hits["bps"][f["bps_source"]] += 1
            if f.get("shares_source") and f.get("shares") is not None:
                alias_hits["shares"][f["shares_source"]] += 1
                shares_covered += 1
            if market_cap is not None:
                market_cap_covered += 1
            if per is not None:
                per_vals.append(per)
                alias_hits["per_method"][per_method or "unknown"] += 1
            if pbr is not None:
                pbr_vals.append(pbr)
                alias_hits["pbr_method"][pbr_method or "unknown"] += 1
            if per is not None or pbr is not None:
                valuation_covered += 1
            elif close_val is None or close_val <= 0:
                uncovered["no_price"] += 1
            elif f.get("eps") is None and f.get("bps") is None and f.get("shares") is None:
                uncovered["no_per_pbr_inputs"] += 1
            else:
                uncovered["nonpositive_or_unusable_inputs"] += 1

            r20, r60, r252 = _return(points, 20), _return(points, 60), _return(points, 252)
            doc = {
                "schema_version": SCHEMA_VERSION, "feature_set": FEATURE_SET,
                "feature_registry_version": FEATURE_REGISTRY_VERSION, "generated_at": generated_at,
                "asof": asof, "provider": PROVIDER, "dataset": "rest:daily_quotes+listed_info+statements",
                "securities_code": code, "entity": _entity(p.get("listed_info") or {}),
                "input": {"source": "jquants_rest", "normalization_version": NORMALIZATION_VERSION},
                "features": {
                    "latest_close": _measured(latest[1] if latest else None, unit="JPY", note="adjusted close when available"),
                    "latest_volume": _measured(latest[2] if latest else None, unit="shares"),
                    "return_20d": _measured(r20, unit="ratio"),
                    "return_60d": _measured(r60, unit="ratio"),
                    "return_252d": _measured(r252, unit="ratio"),
                    "sales_growth_yoy": _measured(f["sales_growth_yoy"], unit="ratio"),
                    "operating_margin": _measured(f["operating_margin"], unit="ratio"),
                    "net_margin": _measured(f["net_margin"], unit="ratio"),
                    "roe_proxy": _measured(f["roe_proxy"], unit="ratio", note="NP / average Eq proxy"),
                    "equity_ratio": _measured(f["equity_ratio"], unit="ratio"),
                    "eps_trailing": _measured(f["eps"], unit="JPY", note="last-FY EPS (REST)"),
                    "bps": _measured(f["bps"], unit="JPY", note="BPS (REST)"),
                    "shares_outstanding": _measured(
                        f["shares"], unit="shares",
                        note=f"shares outstanding alias: {f.get('shares_source') or 'UNKNOWN'}",
                    ),
                    "market_cap_jpy": _measured(
                        market_cap, unit="JPY",
                        note="latest_close * shares_outstanding; trailing point-in-time proxy",
                    ),
                    "per_trailing": _measured(per, unit="x", note="trailing: latest_close / last-FY EPS (or close*shares/NP)"),
                    "pbr": _measured(pbr, unit="x", note="latest_close / BPS (or close*shares/Eq)"),
                    "dividend_record_present": _measured(None, unit="bool"),
                },
                "source_dates": {
                    "latest_price_date": latest[0].isoformat() if latest else None,
                    "latest_financial_disclosure_date": f["latest_disclosure_date"],
                    "latest_dividend_pub_date": None,
                },
                "source_snapshot": {
                    "financial_current_period": f.get("current_period"),
                    "financial_previous_period": f.get("previous_period"),
                    "used_fields": f.get("used_fields") or {},
                },
                "warnings": ["not_a_recommendation", "not_a_ranking", "roe_proxy_is_not_audited_roe"],
            }
            fh.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")

    n = len(codes)
    manifest = {
        "schema_version": SCHEMA_VERSION, "feature_set": FEATURE_SET,
        "generated_at": generated_at, "asof": asof, "provider": PROVIDER,
        "input": {"source": "jquants_rest", "requested_codes": n},
        "coverage": {
            "listed_codes": n, "price_covered": price_covered, "summary_covered": summary_covered,
            "valuation_covered": valuation_covered,
            "latest_price_date": latest_price_date.isoformat() if latest_price_date else None,
            "price_coverage_ratio": price_covered / n if n else None,
            "summary_coverage_ratio": summary_covered / n if n else None,
            "valuation_coverage_ratio": valuation_covered / n if n else None,
            "valuation_uncovered_reasons": dict(uncovered),
            "shares_covered": shares_covered,
            "shares_coverage_ratio": shares_covered / n if n else None,
            "market_cap_covered": market_cap_covered,
            "market_cap_coverage_ratio": market_cap_covered / n if n else None,
        },
        "valuation_alias_hits": {k: dict(v) for k, v in alias_hits.items()},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                             encoding="utf-8")
    return {"provider": PROVIDER, "feature_set": FEATURE_SET, "asof": asof,
            "feature_rows": n, "features_path": features_path, "manifest_path": manifest_path,
            "coverage": manifest["coverage"]}


def fetch_and_build(*, codes: list[str], asof: str, client=None, derived_root: Path | None = None) -> dict:
    """Fetch REST payloads per code via the network client, then build derived."""
    if client is None:
        from radar.sources.jquants_rest_client import JQuantsRestClient
        client = JQuantsRestClient()
    asof = _valid_asof(asof)
    start = (date.fromisoformat(asof) - timedelta(days=430)).isoformat()
    payloads = {}
    for code in codes:
        payloads[code] = {
            "daily_quotes": client.daily_quotes(code=code, date_from=start, date_to=asof),
            "listed_info": client.listed_info(code=code),
            "statements": client.statements(code=code),
        }
    return build_jquants_features_from_payloads(payloads=payloads, asof=asof, derived_root=derived_root)
