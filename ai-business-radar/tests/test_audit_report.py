"""Data-quality audit report tests (cross-check aggregate + valuation coverage)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.research.audit_report import build_audit_report, render_audit_report
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent


def _m(value, unit="ratio", status="CALCULATION"):
    if value is None:
        status = "UNKNOWN"
    return {"value": value, "status": status, "unit": unit, "classification": "own",
            "source_fields": [], "note": None}


def _write_edinet(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_financials_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "feature_set": "edinet_financials_v1", "asof": asof, "edinet_code": "E02367",
        "input": {"raw_hash_normalized": "h", "raw_hash_compressed": "h"},
        "features": {
            "revenue_growth_yoy": _m(0.12),
            "operating_margin": _m(0.08),   # vs J-Quants 0.20 -> mismatch (>2pt)
            "net_margin": _m(0.04),
            "valuation_status": _m(None),
        },
    }
    (d / "E02367.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _write_company_map(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_company_map_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    (d / "companies.jsonl").write_text(json.dumps({
        "feature_set": "edinet_company_map_v1", "asof": asof,
        "edinet_code": "E02367", "securities_code": "72030", "sec_code": "72030",
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"feature_set": "edinet_company_map_v1", "asof": asof}),
                                     encoding="utf-8")


def _write_jquants(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "jquants_equity_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    (d / "features.jsonl").write_text(json.dumps({
        "feature_set": "jquants_equity_v1", "asof": asof, "securities_code": "72030",
        "entity": {"market": "プライム", "sector33": "輸送用機器"}, "input": {},
        "features": {
            "latest_close": _m(2530, unit="JPY"),
            "per_trailing": _m(12.6, unit="x"), "pbr": _m(1.0, unit="x"),
            "revenue_growth_yoy": _m(0.12), "sales_growth_yoy": _m(0.12),
            "operating_margin": _m(0.20),   # mismatch vs EDINET 0.08
            "net_margin": _m(0.04),
        },
        "source_dates": {"latest_price_date": asof},
    }, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({
        "feature_set": "jquants_equity_v1", "asof": asof,
        "coverage": {
            "listed_codes": 100, "valuation_covered": 84, "price_covered": 98,
            "valuation_coverage_ratio": 0.84, "price_coverage_ratio": 0.98,
            "valuation_uncovered_reasons": {"no_per_pbr_inputs": 10, "nonpositive_or_unusable_inputs": 4, "no_price": 2},
        },
        "valuation_alias_hits": {"eps": {"EPS": 80}, "bps": {"BPS": 83}, "per_method": {"eps:EPS": 80}},
    }, ensure_ascii=False, sort_keys=True), encoding="utf-8")


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        _write_edinet(self.base)
        _write_company_map(self.base)
        _write_jquants(self.base)
        self.derived = self.base / "data" / "derived"

    def tearDown(self):
        self.td.cleanup()

    def test_cross_check_aggregation_counts_mismatch(self):
        report = build_audit_report(asof="2026-06-18", derived_root=self.derived)
        cc = report["cross_check"]
        self.assertEqual(cc["cross_checked_items"], 1)
        om = cc["metrics"]["operating_margin↔operating_margin"]
        self.assertEqual(om["checked"], 1)
        self.assertEqual(om["mismatch"], 1)             # 0.08 vs 0.20 exceeds 2pt
        rg = cc["metrics"]["revenue_growth_yoy↔sales_growth_yoy"]
        self.assertEqual(rg["mismatch"], 0)             # 0.12 vs 0.12 within tolerance

    def test_valuation_coverage_view_surfaces_reasons(self):
        report = build_audit_report(asof="2026-06-18", derived_root=self.derived)
        val = report["valuation"]
        self.assertAlmostEqual(val["valuation_coverage_ratio"], 0.84)
        self.assertEqual(val["valuation_uncovered_reasons"]["no_per_pbr_inputs"], 10)
        self.assertIn("eps", val["valuation_alias_hits"])

    def test_render_is_clean(self):
        report = build_audit_report(asof="2026-06-18", derived_root=self.derived)
        text = render_audit_report(report)
        self.assertIn("cross-check", text)
        self.assertIn("valuation coverage", text)
        self.assertIn("uncovered_reasons", text)
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_valuation_only_when_no_edinet(self):
        """Report still works (valuation section) when EDINET derived is absent."""
        import shutil
        shutil.rmtree(self.derived / "features" / "edinet_financials_v1")
        report = build_audit_report(asof="2026-06-18", derived_root=self.derived)
        self.assertIn("reason", report["cross_check"])   # cross-check gracefully unavailable
        self.assertAlmostEqual(report["valuation"]["valuation_coverage_ratio"], 0.84)

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "audit-report", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
