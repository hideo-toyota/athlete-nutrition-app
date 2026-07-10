"""investor-brief tests: works on J-Quants alone; Human Review List needs EDINET."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.research.investor_brief import build_investor_brief, render_investor_brief, write_investor_brief
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent


def _m(value, unit="ratio", status="CALCULATION"):
    if value is None:
        status = "UNKNOWN"
    return {"value": value, "status": status, "unit": unit, "classification": "own",
            "source_fields": [], "note": None}


def _jq_doc(code, close, per, pbr, r20, asof="2026-06-18"):
    return {
        "feature_set": "jquants_equity_v1", "asof": asof, "securities_code": code,
        "entity": {"market": "プライム", "sector33": "輸送用機器"}, "input": {},
        "features": {
            "latest_close": _m(close, unit="JPY"), "market_cap_jpy": _m(close * 1_000_000, unit="JPY"),
            "per_trailing": _m(per, unit="x"), "pbr": _m(pbr, unit="x"),
            "return_20d": _m(r20), "return_60d": _m(-0.02), "return_252d": _m(0.12),
        },
        "source_dates": {"latest_price_date": asof},
    }


def _write_jquants(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "jquants_equity_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    with (d / "features.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(_jq_doc("72030", 2500, 12.5, 1.1, -0.08), ensure_ascii=False) + "\n")
        fh.write(json.dumps(_jq_doc("67580", 1800, 18.0, 2.0, 0.09), ensure_ascii=False) + "\n")
    (d / "manifest.json").write_text(json.dumps({
        "feature_set": "jquants_equity_v1", "asof": asof,
        "coverage": {"listed_codes": 2, "price_covered": 2, "valuation_covered": 2,
                     "latest_price_date": asof, "price_coverage_ratio": 1.0,
                     "valuation_coverage_ratio": 1.0, "market_cap_coverage_ratio": 1.0},
        "distribution": {
            "per_trailing": {"count": 2, "median": 15.25, "positive_rate": 1.0},
            "pbr": {"count": 2, "median": 1.55, "positive_rate": 1.0},
            "market_cap_jpy": {"count": 2, "median": 2_150_000_000, "positive_rate": 1.0},
            "return_20d": {"count": 2, "median": 0.005, "positive_rate": 0.5},
            "return_60d": {"count": 2, "median": -0.02, "positive_rate": 0.0},
            "return_252d": {"count": 2, "median": 0.12, "positive_rate": 1.0},
        },
    }, ensure_ascii=False), encoding="utf-8")


def _write_edinet(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_financials_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    (d / "E02367.json").write_text(json.dumps({
        "feature_set": "edinet_financials_v1", "asof": asof, "edinet_code": "E02367",
        "input": {"raw_hash_normalized": "h"},
        "features": {"revenue_growth_yoy": _m(0.12), "operating_margin": _m(0.08),
                     "valuation_status": _m(None)},
    }, ensure_ascii=False), encoding="utf-8")
    cm = base / "data" / "derived" / "features" / "edinet_company_map_v1" / asof
    cm.mkdir(parents=True, exist_ok=True)
    (cm / "companies.jsonl").write_text(json.dumps({
        "feature_set": "edinet_company_map_v1", "asof": asof,
        "edinet_code": "E02367", "securities_code": "72030", "sec_code": "72030"}) + "\n", encoding="utf-8")
    (cm / "manifest.json").write_text(json.dumps({"feature_set": "edinet_company_map_v1", "asof": asof}),
                                      encoding="utf-8")


class InvestorBriefTests(unittest.TestCase):
    def test_jquants_only_brief_works(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_jquants(base)  # no EDINET on purpose
            brief = build_investor_brief(asof="2026-06-18", derived_root=base / "data" / "derived")
            self.assertEqual(brief["market_snapshot"]["status"], "CALCULATION")
            self.assertEqual(brief["human_review_list"], [])  # no EDINET -> empty, not crash
            text = render_investor_brief(brief)
        self.assertIn("Market Snapshot", text)
        self.assertIn("15.25x", text)  # PER median from manifest distribution
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_with_edinet_human_review_can_populate(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_jquants(base)
            _write_edinet(base)
            brief = build_investor_brief(asof="2026-06-18", derived_root=base / "data" / "derived")
            self.assertEqual(brief["market_snapshot"]["status"], "CALCULATION")
            self.assertGreaterEqual(brief["counts"]["research_items"], 1)
            text = render_investor_brief(brief)
            with tempfile.TemporaryDirectory() as od:
                res = write_investor_brief(brief, outputs_root=Path(od))
                self.assertTrue(Path(res["md_path"]).exists())
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_no_data_skips_cleanly(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            with self.assertRaises(SystemExit):
                build_investor_brief(asof="2026-06-18", derived_root=base / "data" / "derived")

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "investor-brief", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
