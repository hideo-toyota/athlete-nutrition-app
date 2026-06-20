"""Build local J-Quants bulk features from already-downloaded CSV gzip files.

No network, no environment variables, no provider raw body in stdout, and no
recommendations/rankings. This module converts local bulk data into auditable
derived features keyed by securities code.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from radar.sources import common

ROOT = Path(__file__).resolve().parent.parent.parent
FEATURE_SET = "jquants_equity_v1"
SCHEMA_VERSION = "1"
FEATURE_REGISTRY_VERSION = "1"
NORMALIZATION_VERSION = "1"
PROVIDER = "jquants"

_ASOF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CODE_RE = re.compile(r"^[0-9A-Z]{4,5}$")
_JST = timezone(timedelta(hours=9))


def _valid_asof(asof: str) -> str:
    if not isinstance(asof, str) or not _ASOF_RE.match(asof):
        raise SystemExit(f"--asof は 'YYYY-MM-DD' で指定してください: {asof}")
    try:
        date.fromisoformat(asof)
    except ValueError as e:
        raise SystemExit(f"--asof が実在しない日付です: {asof}") from e
    return asof


def _inside(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
    except ValueError:
        return False
    return True


def _raw_root(raw_root: Path | None) -> Path:
    root = Path(raw_root or (ROOT / "data" / "raw" / "jquants" / "bulk"))
    if not root.is_absolute():
        root = ROOT / root
    root = root.resolve()
    expected = (ROOT / "data" / "raw" / "jquants" / "bulk").resolve()
    if raw_root is None and not root.exists():
        raise SystemExit(f"J-Quants bulk raw が見つかりません: {root}")
    # Test callers may pass a temp root, but production default is fixed.
    if raw_root is None and not _inside(root, expected):
        raise SystemExit("J-Quants raw root が data/raw/jquants/bulk 配下ではありません")
    return root


def _output_dir(derived_root: Path | None, asof: str) -> Path:
    root = Path(derived_root or (ROOT / "data" / "derived"))
    if not root.is_absolute():
        root = ROOT / root
    base = (root.resolve() / "features" / FEATURE_SET / asof).resolve()
    base.mkdir(parents=True, exist_ok=True)
    if not _inside(base, root.resolve()):
        raise SystemExit("derived 出力先が data/derived 配下を脱出しています")
    return base


def _date_or_none(value) -> date | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text == "-":
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _float_or_none(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text or text in {"-", "nan", "NaN", "inf", "-inf", "Infinity"}:
            return None
        try:
            out = float(text)
        except ValueError:
            return None
        return out if math.isfinite(out) else None
    return None


def _rows(path: Path):
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as fh:
            yield from csv.DictReader(fh)
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise SystemExit(f"J-Quants bulk CSV を読めません: {path.name}") from e


def _extract_file_date(path: Path) -> date | None:
    m = re.search(r"_(\d{8})\.csv\.gz$", path.name)
    if m:
        try:
            return date.fromisoformat(f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}")
        except ValueError:
            return None
    m = re.search(r"_(\d{6})\.csv\.gz$", path.name)
    if m:
        try:
            return date.fromisoformat(f"{m.group(1)[:4]}-{m.group(1)[4:6]}-01")
        except ValueError:
            return None
    return None


def _all_gz(root: Path, relative: str) -> list[Path]:
    base = root / relative
    if not base.exists():
        return []
    return sorted(base.glob("**/*.gz"))


def _select_latest_file(root: Path, relative: str, asof_date: date) -> Path:
    candidates = []
    for path in _all_gz(root, relative):
        fd = _extract_file_date(path)
        if fd is not None and fd <= asof_date:
            candidates.append(path)
    if not candidates:
        raise SystemExit(f"J-Quants bulk file がありません: {relative} <= {asof_date}")
    return candidates[-1]


def _select_range_files(root: Path, relative: str, start: date, end: date) -> list[Path]:
    out = []
    for path in _all_gz(root, relative):
        fd = _extract_file_date(path)
        if fd is None:
            continue
        # Monthly files are stamped first-of-month; include full month if overlap.
        if len(re.search(r"_(\d{6,8})\.csv\.gz$", path.name).group(1)) == 6:
            month_end = (date(fd.year + (1 if fd.month == 12 else 0), 1 if fd.month == 12 else fd.month + 1, 1)
                         - timedelta(days=1))
            if month_end < start or fd > end:
                continue
        elif fd < start or fd > end:
            continue
        out.append(path)
    return sorted(out)


def _hash_files(paths: list[Path]) -> tuple[str, list[dict]]:
    entries = []
    for path in sorted(paths):
        raw_hash = common.hash_bytes(path.read_bytes())
        entries.append({
            "path": str(path),
            "size": path.stat().st_size,
            "raw_hash_compressed": raw_hash,
        })
    manifest_payload = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(manifest_payload).hexdigest(), entries


def _measured(value, *, unit: str, status: str | None = None, note: str | None = None):
    if value is None:
        status = "UNKNOWN"
    return {
        "value": value,
        "status": status or "CALCULATION",
        "unit": unit,
        "classification": "own",
        "note": note,
    }


def _ratio(num, den):
    if num is None or den is None or den <= 0:
        return None
    return num / den


def _median(values):
    clean = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return statistics.median(clean) if clean else None


def _pct(values, pred):
    clean = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
    return (sum(1 for v in clean if pred(v)) / len(clean)) if clean else None


def _quantile(values, index: int):
    clean = sorted(v for v in values if isinstance(v, (int, float)) and math.isfinite(v))
    if len(clean) < 10:
        return None
    return statistics.quantiles(clean, n=10)[index]


def _load_master(root: Path, asof_date: date) -> tuple[dict[str, dict], Path]:
    path = _select_latest_file(root, "equities/master", asof_date)
    master = {}
    for row in _rows(path):
        code = str(row.get("Code", "")).strip().upper()
        d = _date_or_none(row.get("Date"))
        if not _CODE_RE.match(code) or d is None or d > asof_date:
            continue
        previous = master.get(code)
        if previous is None or d >= previous["date"]:
            master[code] = {
                "date": d,
                "code": code,
                "company_name": row.get("CoName") or row.get("CoNameEn") or "",
                "market": row.get("MktNm") or row.get("Mkt") or "",
                "sector33": row.get("S33Nm") or row.get("S33") or "",
                "margin_type": row.get("MrgnNm") or row.get("Mrgn") or "",
                "scale_category": row.get("ScaleCat") or "",
            }
    return master, path


def _load_prices(root: Path, asof_date: date) -> tuple[dict[str, list[tuple[date, float, float | None]]], list[Path]]:
    # Calendar days are deliberately wider than 252 trading days.
    files = _select_range_files(root, "equities/bars/daily/premium", asof_date - timedelta(days=430), asof_date)
    by_code: dict[str, list[tuple[date, float, float | None]]] = defaultdict(list)
    for path in files:
        for row in _rows(path):
            code = str(row.get("Code", "")).strip().upper()
            d = _date_or_none(row.get("Date"))
            if not _CODE_RE.match(code) or d is None or d > asof_date:
                continue
            close = _float_or_none(row.get("AC"))
            if close is None:
                close = _float_or_none(row.get("C"))
            volume = _float_or_none(row.get("AVo"))
            if volume is None:
                volume = _float_or_none(row.get("Vo"))
            if close is not None and close > 0:
                by_code[code].append((d, close, volume))
    for values in by_code.values():
        values.sort(key=lambda x: x[0])
    return by_code, files


def _load_summary(root: Path, asof_date: date) -> tuple[dict[str, list[dict]], list[Path]]:
    files = _all_gz(root, "fins/summary")
    by_code: dict[str, list[dict]] = defaultdict(list)
    for path in files:
        for row in _rows(path):
            code = str(row.get("Code", "")).strip().upper()
            disc = _date_or_none(row.get("DiscDate"))
            if not _CODE_RE.match(code) or disc is None or disc > asof_date:
                continue
            doc_type = str(row.get("DocType", ""))
            cur_type = str(row.get("CurPerType", ""))
            if cur_type == "FY" and "FinancialStatements" in doc_type:
                by_code[code].append(row)
    for values in by_code.values():
        values.sort(key=lambda r: (r.get("CurPerEn", ""), r.get("DiscDate", ""), r.get("DiscTime", ""), r.get("DiscNo", "")))
    return by_code, files


def _load_dividends(root: Path, asof_date: date) -> tuple[dict[str, dict], list[Path]]:
    files = _all_gz(root, "fins/dividend")
    latest = {}
    for path in files:
        for row in _rows(path):
            code = str(row.get("Code", "")).strip().upper()
            pub = _date_or_none(row.get("PubDate"))
            if not _CODE_RE.match(code) or pub is None or pub > asof_date:
                continue
            stamp = (row.get("PubDate", ""), row.get("PubTime", ""), row.get("RefNo", ""))
            if code not in latest or stamp > latest[code][0]:
                latest[code] = (stamp, row)
    return {code: row for code, (_, row) in latest.items()}, files


def _return(points: list[tuple[date, float, float | None]], periods: int):
    if len(points) <= periods:
        return None
    base = points[-1 - periods][1]
    last = points[-1][1]
    if base <= 0:
        return None
    return last / base - 1


# Per-share / share-count column aliases. Real bulk column names must be verified
# against raw on the Mac; coverage in the summary tells whether an alias matched.
_EPS_KEYS = ("EPS", "EPSCons", "EarningsPerShare")
_BPS_KEYS = ("BPS", "BPSCons", "BookValuePerShare")
_SHARES_KEYS = ("Shares", "ShEoF", "ShsEoF", "IssuedShares", "NumShares")


def _first_float(row: dict, keys: tuple[str, ...]):
    value, _ = _first_float_with_key(row, keys)
    return value


def _first_float_with_key(row: dict, keys: tuple[str, ...]):
    for k in keys:
        v = _float_or_none(row.get(k))
        if v is not None:
            return v, k
    return None, None


def _financial_features(rows: list[dict]):
    current = rows[-1] if rows else None
    previous = rows[-2] if len(rows) >= 2 else None
    if current is None:
        return {
            "latest_disclosure_date": None,
            "sales_growth_yoy": None,
            "operating_margin": None,
            "net_margin": None,
            "roe_proxy": None,
            "equity_ratio": None,
            "eps": None,
            "bps": None,
            "eps_source": None,
            "bps_source": None,
            "shares": None,
            "shares_source": None,
            "net_profit": None,
            "equity": None,
        }
    sales = _float_or_none(current.get("Sales"))
    prev_sales = _float_or_none(previous.get("Sales")) if previous else None
    op = _float_or_none(current.get("OP"))
    np = _float_or_none(current.get("NP"))
    eq = _float_or_none(current.get("Eq"))
    prev_eq = _float_or_none(previous.get("Eq")) if previous else None
    ta = _float_or_none(current.get("TA"))
    avg_eq = ((eq + prev_eq) / 2) if eq is not None and prev_eq is not None else None
    eps, eps_source = _first_float_with_key(current, _EPS_KEYS)
    bps, bps_source = _first_float_with_key(current, _BPS_KEYS)
    shares, shares_source = _first_float_with_key(current, _SHARES_KEYS)
    return {
        "latest_disclosure_date": current.get("DiscDate"),
        "sales_growth_yoy": (sales / prev_sales - 1) if sales is not None and prev_sales is not None and prev_sales > 0 else None,
        "operating_margin": _ratio(op, sales),
        "net_margin": _ratio(np, sales),
        "roe_proxy": _ratio(np, avg_eq),
        "equity_ratio": _ratio(eq, ta),
        "eps": eps,
        "bps": bps,
        "eps_source": eps_source,
        "bps_source": bps_source,
        "shares": shares,
        "shares_source": shares_source,
        "net_profit": np,
        "equity": eq,
    }


def _per_pbr(close, fin: dict):
    """Trailing PER/PBR from current price + last-FY per-share (or totals + shares).

    Zero/negative earnings or equity -> UNKNOWN (None), never a misleading number.
    """
    if close is None or close <= 0:
        return None, None, None, None
    per = pbr = None
    per_method = pbr_method = None
    eps, bps = fin.get("eps"), fin.get("bps")
    shares, net_profit, equity = fin.get("shares"), fin.get("net_profit"), fin.get("equity")
    if eps is not None and eps > 0:
        per = round(close / eps, 2)
        per_method = f"eps:{fin.get('eps_source') or 'unknown'}"
    elif shares and shares > 0 and net_profit is not None and net_profit > 0:
        per = round(close * shares / net_profit, 2)
        per_method = f"shares_net_profit:{fin.get('shares_source') or 'unknown'}"
    if bps is not None and bps > 0:
        pbr = round(close / bps, 2)
        pbr_method = f"bps:{fin.get('bps_source') or 'unknown'}"
    elif shares and shares > 0 and equity is not None and equity > 0:
        pbr = round(close * shares / equity, 2)
        pbr_method = f"shares_equity:{fin.get('shares_source') or 'unknown'}"
    return per, pbr, per_method, pbr_method


def _per_uncovered_reason(close, fin: dict) -> str:
    if close is None or close <= 0:
        return "no_price"
    shares = fin.get("shares")
    if fin.get("eps") is None and not (shares and shares > 0 and fin.get("net_profit") is not None):
        return "no_per_inputs"
    return "nonpositive_or_unusable_inputs"


def _pbr_uncovered_reason(close, fin: dict) -> str:
    if close is None or close <= 0:
        return "no_price"
    shares = fin.get("shares")
    if fin.get("bps") is None and not (shares and shares > 0 and fin.get("equity") is not None):
        return "no_pbr_inputs"
    return "nonpositive_or_unusable_inputs"


def _valuation_uncovered_reason(per_reason: str, pbr_reason: str) -> str:
    if per_reason == "no_price" and pbr_reason == "no_price":
        return "no_price"
    if per_reason == "nonpositive_or_unusable_inputs" and pbr_reason == "nonpositive_or_unusable_inputs":
        return "nonpositive_or_unusable_inputs"
    if per_reason == "no_per_inputs" or pbr_reason == "no_pbr_inputs":
        return "no_per_pbr_inputs"
    return "mixed_unusable_inputs"


def _format_ratio(value):
    return "UNKNOWN" if value is None else f"{value * 100:.1f}%"


def _format_distribution_value(key: str, value):
    if value is None:
        return "UNKNOWN"
    if key in {"per_trailing", "pbr"}:
        return f"{value:.2f}x"
    return _format_ratio(value)


def build_jquants_bulk_features(
    *,
    asof: str,
    raw_root: Path | None = None,
    derived_root: Path | None = None,
    clock=None,
) -> dict:
    asof = _valid_asof(asof)
    asof_date = date.fromisoformat(asof)
    root = _raw_root(raw_root)
    out_dir = _output_dir(derived_root, asof)

    master, master_file = _load_master(root, asof_date)
    prices, price_files = _load_prices(root, asof_date)
    summaries, summary_files = _load_summary(root, asof_date)
    dividends, dividend_files = _load_dividends(root, asof_date)
    input_files = [master_file, *price_files, *summary_files, *dividend_files]
    input_digest, input_manifest = _hash_files(input_files)

    generated = clock() if clock else datetime.now(timezone.utc)
    if generated.tzinfo is None:
        generated = generated.replace(tzinfo=timezone.utc)
    generated_at = generated.astimezone(timezone.utc).isoformat(timespec="seconds")

    features_path = out_dir / "features.jsonl"
    summary_path = out_dir / "summary.md"
    manifest_path = out_dir / "manifest.json"
    if not _inside(features_path.resolve(), out_dir):
        raise SystemExit("features 出力先が jquants derived 配下を脱出しています")

    market_counts = Counter()
    sector_counts = Counter()
    ret20 = []
    ret60 = []
    ret252 = []
    sales_growth = []
    op_margin = []
    roe = []
    per_vals = []
    pbr_vals = []
    valuation_covered = 0
    valuation_uncovered_reasons = Counter()
    per_covered = 0
    pbr_covered = 0
    per_uncovered_reasons = Counter()
    pbr_uncovered_reasons = Counter()
    valuation_alias_hits = {
        "eps": Counter(),
        "bps": Counter(),
        "shares": Counter(),
        "per_method": Counter(),
        "pbr_method": Counter(),
    }
    price_covered = 0
    summary_covered = 0
    dividend_covered = 0
    latest_price_date = None

    with features_path.open("w", encoding="utf-8") as fh:
        for code in sorted(master):
            m = master[code]
            market_counts[m["market"]] += 1
            sector_counts[m["sector33"]] += 1
            points = prices.get(code, [])
            latest = points[-1] if points else None
            if latest:
                price_covered += 1
                latest_price_date = latest[0] if latest_price_date is None or latest[0] > latest_price_date else latest_price_date
            f = _financial_features(summaries.get(code, []))
            if summaries.get(code):
                summary_covered += 1
            div = dividends.get(code)
            if div:
                dividend_covered += 1
            r20 = _return(points, 20)
            r60 = _return(points, 60)
            r252 = _return(points, 252)
            for bucket, value in ((ret20, r20), (ret60, r60), (ret252, r252)):
                if value is not None:
                    bucket.append(value)
            if f["sales_growth_yoy"] is not None:
                sales_growth.append(f["sales_growth_yoy"])
            if f["operating_margin"] is not None:
                op_margin.append(f["operating_margin"])
            if f["roe_proxy"] is not None:
                roe.append(f["roe_proxy"])
            close_val = latest[1] if latest else None
            per, pbr, per_method, pbr_method = _per_pbr(close_val, f)
            per_reason = _per_uncovered_reason(close_val, f) if per is None else None
            pbr_reason = _pbr_uncovered_reason(close_val, f) if pbr is None else None
            if f.get("eps_source") and f.get("eps") is not None:
                valuation_alias_hits["eps"][f["eps_source"]] += 1
            if f.get("bps_source") and f.get("bps") is not None:
                valuation_alias_hits["bps"][f["bps_source"]] += 1
            if f.get("shares_source") and f.get("shares") is not None:
                valuation_alias_hits["shares"][f["shares_source"]] += 1
            if per is not None:
                per_vals.append(per)
                per_covered += 1
                valuation_alias_hits["per_method"][per_method or "unknown"] += 1
            else:
                per_uncovered_reasons[per_reason] += 1
            if pbr is not None:
                pbr_vals.append(pbr)
                pbr_covered += 1
                valuation_alias_hits["pbr_method"][pbr_method or "unknown"] += 1
            else:
                pbr_uncovered_reasons[pbr_reason] += 1
            if per is not None or pbr is not None:
                valuation_covered += 1
            else:
                valuation_uncovered_reasons[_valuation_uncovered_reason(per_reason, pbr_reason)] += 1

            doc = {
                "schema_version": SCHEMA_VERSION,
                "feature_set": FEATURE_SET,
                "feature_registry_version": FEATURE_REGISTRY_VERSION,
                "generated_at": generated_at,
                "asof": asof,
                "provider": PROVIDER,
                "dataset": "bulk:master+prices+financials+dividends",
                "securities_code": code,
                "entity": {
                    "company_name": m["company_name"],
                    "market": m["market"],
                    "sector33": m["sector33"],
                    "margin_type": m["margin_type"],
                    "master_date": m["date"].isoformat(),
                },
                "input": {
                    "raw_root": str(root),
                    "input_manifest_digest": input_digest,
                    "normalization_version": NORMALIZATION_VERSION,
                },
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
                    "eps_trailing": _measured(f["eps"], unit="JPY", note="last-FY EPS (bulk alias; verify coverage)"),
                    "bps": _measured(f["bps"], unit="JPY", note="BPS (bulk alias; verify coverage)"),
                    "per_trailing": _measured(per, unit="x", note="trailing: latest_close / last-FY EPS (or close*shares/NP)"),
                    "pbr": _measured(pbr, unit="x", note="latest_close / BPS (or close*shares/Eq)"),
                    "dividend_record_present": _measured(bool(div), unit="bool", status="CALCULATION"),
                },
                "source_dates": {
                    "latest_price_date": latest[0].isoformat() if latest else None,
                    "latest_financial_disclosure_date": f["latest_disclosure_date"],
                    "latest_dividend_pub_date": div.get("PubDate") if div else None,
                },
                "warnings": [
                    "not_a_recommendation",
                    "not_a_ranking",
                    "roe_proxy_is_not_audited_roe",
                ],
            }
            fh.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")

    def dist(values):
        return {
            "count": len(values),
            "median": _median(values),
            "positive_rate": _pct(values, lambda v: v > 0),
            "p10": _quantile(values, 0),
            "p90": _quantile(values, 8),
        }

    summary = {
        "schema_version": SCHEMA_VERSION,
        "feature_set": FEATURE_SET,
        "generated_at": generated_at,
        "asof": asof,
        "provider": PROVIDER,
        "input": {
            "raw_root": str(root),
            "input_file_count": len(input_files),
            "input_manifest_digest": input_digest,
            "input_manifest": input_manifest,
        },
        "coverage": {
            "listed_codes": len(master),
            "price_covered": price_covered,
            "summary_covered": summary_covered,
            "dividend_covered": dividend_covered,
            "latest_price_date": latest_price_date.isoformat() if latest_price_date else None,
            "price_coverage_ratio": price_covered / len(master) if master else None,
            "summary_coverage_ratio": summary_covered / len(master) if master else None,
            "dividend_coverage_ratio": dividend_covered / len(master) if master else None,
            "valuation_covered": valuation_covered,
            "valuation_coverage_ratio": valuation_covered / len(master) if master else None,
            "valuation_uncovered_reasons": dict(valuation_uncovered_reasons),
            "per_covered": per_covered,
            "per_coverage_ratio": per_covered / len(master) if master else None,
            "per_uncovered_reasons": dict(per_uncovered_reasons),
            "pbr_covered": pbr_covered,
            "pbr_coverage_ratio": pbr_covered / len(master) if master else None,
            "pbr_uncovered_reasons": dict(pbr_uncovered_reasons),
        },
        "distribution": {
            "return_20d": dist(ret20),
            "return_60d": dist(ret60),
            "return_252d": dist(ret252),
            "sales_growth_yoy": dist(sales_growth),
            "operating_margin": dist(op_margin),
            "roe_proxy": dist(roe),
            "per_trailing": dist(per_vals),
            "pbr": dist(pbr_vals),
        },
        "valuation_alias_hits": {k: dict(v) for k, v in valuation_alias_hits.items()},
        "market_counts": market_counts.most_common(),
        "sector33_counts_top": sector_counts.most_common(20),
        "warnings": [
            "This is a local derived feature set, not a buy/sell recommendation.",
            "No ranking or expected return is emitted.",
            "J-Quants raw data is not copied to stdout or outputs.",
        ],
    }
    manifest_path.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# J-Quants Equity Features",
        "",
        f"- asof: {asof}",
        f"- generated_at: {generated_at}",
        "- scope: local derived features only; no recommendation, no ranking.",
        f"- features_jsonl: `{features_path}`",
        f"- manifest: `{manifest_path}`",
        f"- input_file_count: {len(input_files)}",
        f"- input_manifest_digest: `{input_digest}`",
        "",
        "## Coverage",
        f"- listed_codes: {len(master)}",
        f"- price_coverage: {_format_ratio(summary['coverage']['price_coverage_ratio'])}",
        f"- summary_coverage: {_format_ratio(summary['coverage']['summary_coverage_ratio'])}",
        f"- valuation_coverage: {_format_ratio(summary['coverage']['valuation_coverage_ratio'])}",
        f"- per_coverage: {_format_ratio(summary['coverage']['per_coverage_ratio'])}",
        f"- pbr_coverage: {_format_ratio(summary['coverage']['pbr_coverage_ratio'])}",
        f"- dividend_coverage: {_format_ratio(summary['coverage']['dividend_coverage_ratio'])}",
        f"- latest_price_date: {summary['coverage']['latest_price_date']}",
        f"- valuation_alias_hits: `{json.dumps(summary['valuation_alias_hits'], ensure_ascii=False, sort_keys=True)}`",
        f"- per_uncovered_reasons: `{json.dumps(summary['coverage']['per_uncovered_reasons'], ensure_ascii=False, sort_keys=True)}`",
        f"- pbr_uncovered_reasons: `{json.dumps(summary['coverage']['pbr_uncovered_reasons'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Distribution",
    ]
    for key, data in summary["distribution"].items():
        lines.append(
            f"- {key}: count={data['count']}, median={_format_distribution_value(key, data['median'])}, "
            f"positive_rate={_format_ratio(data['positive_rate'])}, "
            f"p10={_format_distribution_value(key, data['p10'])}, p90={_format_distribution_value(key, data['p90'])}"
        )
    lines.extend([
        "",
        "## Warnings",
        "- This is not investment advice.",
        "- This is not a buy candidate list.",
        "- Values are derived from local J-Quants bulk files and require downstream audit before decision use.",
        "",
    ])
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "provider": PROVIDER,
        "dataset": "bulk",
        "feature_set": FEATURE_SET,
        "asof": asof,
        "listed_codes": len(master),
        "feature_rows": len(master),
        "input_file_count": len(input_files),
        "input_manifest_digest": input_digest,
        "features_path": features_path,
        "summary_path": summary_path,
        "manifest_path": manifest_path,
        "coverage": summary["coverage"],
    }
