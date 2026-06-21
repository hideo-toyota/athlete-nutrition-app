"""J-Quants REST -> derived feature builder tests (no network; injected payloads)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.features.jquants_rest import build_jquants_features_from_payloads, fetch_and_build

ROOT = Path(__file__).resolve().parent.parent


def _daily(code, start_close, n=260):
    rows = []
    for i in range(n):
        # ascending dates across two months ending 2026-06-18
        m, d = (5, (i % 28) + 1) if i < 130 else (6, ((i - 130) % 18) + 1)
        rows.append({"Date": f"2026-{m:02d}-{d:02d}", "Code": code,
                     "Close": start_close + i, "AdjustmentClose": start_close + i,
                     "Volume": 1000 + i, "AdjustmentVolume": 1000 + i})
    return {"daily_quotes": rows}


def _statements(code):
    return {"statements": [
        {"Code": code, "DisclosedDate": "2025-05-10", "TypeOfCurrentPeriod": "FY",
         "CurrentPeriodEndDate": "2025-03-31", "NetSales": "1000", "OperatingProfit": "80",
         "Profit": "50", "Equity": "400", "TotalAssets": "2000",
         "EarningsPerShare": "16", "BookValuePerShare": "200"},
        {"Code": code, "DisclosedDate": "2026-05-10", "TypeOfCurrentPeriod": "FY",
         "CurrentPeriodEndDate": "2026-03-31", "NetSales": "1200", "OperatingProfit": "120",
         "Profit": "60", "Equity": "500", "TotalAssets": "2200",
         "EarningsPerShare": "20", "BookValuePerShare": "250"},
    ]}


def _payloads():
    return {"7203": {
        "daily_quotes": _daily("72030", 100),
        "listed_info": {"info": [{"Code": "72030", "CompanyName": "トヨタ自動車",
                                  "Sector33CodeName": "輸送用機器", "MarketCodeName": "プライム"}]},
        "statements": _statements("72030"),
    }}


class JquantsRestBuildTests(unittest.TestCase):
    def test_builds_same_schema_with_per_pbr(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            res = build_jquants_features_from_payloads(
                payloads=_payloads(), asof="2026-06-18", derived_root=base / "data" / "derived")
            doc = json.loads(Path(res["features_path"]).read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(doc["feature_set"], "jquants_equity_v1")
        self.assertEqual(doc["securities_code"], "72030")          # 4-digit normalized to 5
        feats = doc["features"]
        close = feats["latest_close"]["value"]
        self.assertEqual(feats["eps_trailing"]["value"], 20.0)     # latest FY EPS
        self.assertAlmostEqual(feats["per_trailing"]["value"], round(close / 20, 2))
        self.assertAlmostEqual(feats["pbr"]["value"], round(close / 250, 2))
        self.assertAlmostEqual(feats["operating_margin"]["value"], 0.1)
        self.assertEqual(doc["entity"]["company_name"], "トヨタ自動車")
        self.assertEqual(doc["source_snapshot"]["financial_current_period"]["period_end"], "2026-03-31")
        self.assertEqual(doc["source_snapshot"]["financial_previous_period"]["period_end"], "2025-03-31")
        self.assertEqual(doc["source_snapshot"]["used_fields"]["current"]["sales"]["field"], "NetSales")

    def test_pit_excludes_future_dates(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            res = build_jquants_features_from_payloads(
                payloads=_payloads(), asof="2026-05-31", derived_root=base / "data" / "derived")
            doc = json.loads(Path(res["features_path"]).read_text(encoding="utf-8").splitlines()[0])
            manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        # asof 2026-05-31: only May prices count -> latest price date is in May
        self.assertTrue(doc["source_dates"]["latest_price_date"].startswith("2026-05"))
        self.assertEqual(manifest["coverage"]["valuation_covered"], 1)

    def test_no_price_is_uncovered_not_fake(self):
        payloads = {"9999": {"daily_quotes": {"daily_quotes": []},
                             "listed_info": {"info": [{"Code": "99990", "CompanyName": "x"}]},
                             "statements": {"statements": []}}}
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            res = build_jquants_features_from_payloads(
                payloads=payloads, asof="2026-06-18", derived_root=base / "data" / "derived")
            doc = json.loads(Path(res["features_path"]).read_text(encoding="utf-8").splitlines()[0])
            manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(doc["features"]["per_trailing"]["status"], "UNKNOWN")
        self.assertEqual(manifest["coverage"]["valuation_uncovered_reasons"].get("no_price"), 1)

    def test_fetch_and_build_with_injected_client(self):
        class FakeClient:
            def daily_quotes(self, *, code, date_from=None, date_to=None):
                return _daily("72030", 100)
            def listed_info(self, *, code):
                return {"info": [{"Code": "72030", "CompanyName": "トヨタ", "MarketCodeName": "プライム"}]}
            def statements(self, *, code):
                return _statements("72030")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            res = fetch_and_build(codes=["7203"], asof="2026-06-18", client=FakeClient(),
                                  derived_root=base / "data" / "derived")
        self.assertEqual(res["feature_rows"], 1)
        self.assertEqual(res["coverage"]["price_covered"], 1)

    def test_feature_builder_has_no_network_imports(self):
        text = (ROOT / "radar" / "features" / "jquants_rest.py").read_text(encoding="utf-8")
        for needle in ("urllib", "requests", "socket"):
            self.assertNotIn(needle, text)   # network stays in radar.sources

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "fetch-jquants", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
