"""Phase D0 deterministic research/evidence tests(no LLM handoff)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.research import (build_evidence, build_llm_handoff, build_research_queue,
                            write_evidence, write_llm_handoff, write_research_queue)
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = "RAW_SENTINEL_SHOULD_NOT_RENDER"


def _measured(value, status="CALCULATION", unit="ratio", fields=None):
    return {
        "value": value,
        "status": status,
        "unit": unit,
        "classification": "own",
        "formula_id": "x_v1",
        "source_fields": fields or [],
        "source_periods": ["current"],
        "raw_hash_normalized": "normalized-hash",
        "raw_hash_compressed": "compressed-hash",
        "note": None,
    }


def _unknown(note="missing"):
    m = _measured(None, status="UNKNOWN", unit=None, fields=[])
    m["note"] = note
    return m


def _write_doc(base: Path, code="E02367", asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_financials_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": "1",
        "feature_set": "edinet_financials_v1",
        "feature_registry_version": "1",
        "generated_at": "2026-06-18T00:00:00+00:00",
        "asof": asof,
        "provider": "edinet-db",
        "dataset": "financials",
        "edinet_code": code,
        "period": "annual",
        "input": {
            "raw_hash_normalized": "normalized-hash",
            "raw_hash_compressed": "compressed-hash",
            "available_at": "2026-06-10T15:33:00+09:00",
            "retrieved_at": "2026-06-18T00:00:00+00:00",
        },
        "source_snapshot": {
            "current_period": {"fiscal_year": 2025},
            "used_fields": {"current": {"revenue": {"field": "revenue", "value": SENTINEL}}},
        },
        "features": {
            "revenue_growth_yoy": _measured(0.12, fields=["revenue", "revenue"]),
            "operating_margin": _measured(0.08, fields=["operating_income", "revenue"]),
            "net_margin": _measured(0.04, fields=["net_income", "revenue"]),
            "roe_proxy": _measured(0.10, fields=["net_income", "net_assets", "net_assets"]),
            "roic_proxy": _unknown("fixed"),
            "fcf_proxy": _measured(130, unit="JPY", fields=["cf_operating", "capex"]),
            "net_cash": _measured(220, unit="JPY", fields=["cash", "ibd_current", "ibd_noncurrent"]),
            "equity_ratio": _measured(0.25, fields=["net_assets", "total_assets"]),
            "valuation_status": _unknown("fixed"),
        },
    }
    p = d / f"{code}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _write_company_map(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_company_map_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    row = {
        "schema_version": "1",
        "feature_set": "edinet_company_map_v1",
        "feature_registry_version": "1",
        "asof": asof,
        "provider": "edinet-db",
        "dataset": "companies",
        "edinet_code": "E02367",
        "securities_code": "72030",
        "sec_code": "72030",
        "listing_status": "listed",
        "industry": "輸送用機器",
        "company_name": SENTINEL,
        "claim": "FACT",
    }
    (d / "companies.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({
        "feature_set": "edinet_company_map_v1",
        "asof": asof,
        "row_count": 1,
    }, ensure_ascii=False), encoding="utf-8")


def _write_jquants(base: Path, asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "jquants_equity_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": "1",
        "feature_set": "jquants_equity_v1",
        "feature_registry_version": "1",
        "generated_at": "2026-06-18T00:00:00+00:00",
        "asof": asof,
        "provider": "jquants",
        "dataset": "bulk:master+prices+financials+dividends",
        "securities_code": "72030",
        "entity": {
            "company_name": SENTINEL,
            "market": "プライム",
            "sector33": "輸送用機器",
            "margin_type": "貸借",
            "master_date": asof,
        },
        "input": {
            "input_manifest_digest": "jq-digest",
            "normalization_version": "1",
            "raw_root": str(base / "data" / "raw" / "jquants" / "bulk"),
        },
        "features": {
            "latest_close": _measured(2530, unit="JPY"),
            "latest_volume": _measured(1234000, unit="shares"),
            "return_20d": _measured(0.05),
            "return_60d": _measured(-0.02),
            "return_252d": _measured(0.12),
            "per_trailing": _measured(12.65, unit="x"),
            "pbr": _measured(1.01, unit="x"),
            "eps_trailing": _measured(200.0, unit="JPY"),
            "bps": _measured(2505.0, unit="JPY"),
            "sales_growth_yoy": _measured(0.12),
            "operating_margin": _measured(0.08),
            "net_margin": _measured(0.04),
            "roe_proxy": _measured(0.10),
            "equity_ratio": _measured(0.25),
            "dividend_record_present": _measured(True, unit="bool"),
        },
        "source_dates": {
            "latest_price_date": "2026-06-18",
            "latest_financial_disclosure_date": "2026-05-10",
            "latest_dividend_pub_date": "2026-05-10",
        },
        "warnings": ["not rendered"],
    }
    (d / "features.jsonl").write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({
        "schema_version": "1",
        "feature_set": "jquants_equity_v1",
        "generated_at": "2026-06-18T00:00:00+00:00",
        "asof": asof,
        "provider": "jquants",
        "coverage": {
            "listed_codes": 1,
            "price_covered": 1,
            "summary_covered": 1,
            "dividend_covered": 1,
            "valuation_covered": 1,
            "latest_price_date": "2026-06-18",
            "price_coverage_ratio": 1.0,
            "summary_coverage_ratio": 1.0,
            "dividend_coverage_ratio": 1.0,
            "valuation_coverage_ratio": 1.0,
        },
        "distribution": {
            "return_20d": {"count": 1, "median": 0.05, "positive_rate": 1.0, "p10": None, "p90": None},
            "return_60d": {"count": 1, "median": -0.02, "positive_rate": 0.0, "p10": None, "p90": None},
            "return_252d": {"count": 1, "median": 0.12, "positive_rate": 1.0, "p10": None, "p90": None},
            "per_trailing": {"count": 1, "median": 12.65, "positive_rate": 1.0, "p10": None, "p90": None},
            "pbr": {"count": 1, "median": 1.01, "positive_rate": 1.0, "p10": None, "p90": None},
        },
        "valuation_alias_hits": {
            "eps": {"EPS": 1},
            "bps": {"BPS": 1},
            "shares": {},
            "per_method": {"eps:EPS": 1},
            "pbr_method": {"bps:BPS": 1},
        },
    }, ensure_ascii=False, sort_keys=True), encoding="utf-8")


class ResearchPhaseDTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        _write_doc(self.base)
        _write_company_map(self.base)
        _write_jquants(self.base)

    def tearDown(self):
        self.td.cleanup()

    def test_research_queue_schema_and_no_forbidden_terms(self):
        q = build_research_queue(asof="2026-06-18", derived_root=self.base / "data" / "derived")
        self.assertEqual(len(q["items"]), 1)
        self.assertEqual(q["items"][0]["type"], "research_item")
        self.assertEqual(q["items"][0]["discipline_status"], "未通過")
        self.assertEqual(q["items"][0]["coverage_priority"], 0)
        self.assertEqual(q["items"][0]["ticker"], "72030")
        self.assertEqual(q["items"][0]["jquants_market_context"]["status"], "matched")
        self.assertIn("valuation_status", q["items"][0]["unknown_features"])
        with tempfile.TemporaryDirectory() as od:
            res = write_research_queue(q, outputs_root=Path(od))
            text = Path(res["md_path"]).read_text(encoding="utf-8")
            self.assertIn("J-Quants local context", text)
            self.assertIn("2,530 JPY", text)
            self.assertIn("12.65 x", text)
            self.assertIn("2026-06-18", text)
            self.assertNotIn(SENTINEL, text)
            for token in FORBIDDEN_OUTPUT_TOKENS:
                self.assertNotIn(token, text)
            self.assertTrue(Path(res["csv_path"]).exists())

    def test_research_queue_ignores_build_manifest_json(self):
        d = self.base / "data" / "derived" / "features" / "edinet_financials_v1" / "2026-06-18"
        (d / "build_manifest.json").write_text(json.dumps({
            "feature_set": "edinet_financials_v1",
            "asof": "2026-06-18",
            "built_count": 1,
        }, ensure_ascii=False), encoding="utf-8")
        q = build_research_queue(asof="2026-06-18", derived_root=self.base / "data" / "derived")
        self.assertEqual(len(q["items"]), 1)
        self.assertEqual(q["items"][0]["edinet_code"], "E02367")

    def test_evidence_uses_features_but_not_source_snapshot_values(self):
        ev = build_evidence("E02367", asof="2026-06-18", derived_root=self.base / "data" / "derived")
        with tempfile.TemporaryDirectory() as od:
            res = write_evidence(ev, outputs_root=Path(od))
            text = Path(res["path"]).read_text(encoding="utf-8")
        self.assertIn("operating_margin", text)
        self.assertIn("8.0%", text)
        self.assertIn("J-Quants market/price context", text)
        self.assertIn("2,530 JPY", text)
        self.assertIn("per_trailing", text)
        self.assertIn("12.65 x", text)
        self.assertIn("EDINET vs J-Quants cross-check", text)
        self.assertIn("within_tolerance", text)
        self.assertIn("return_60d", text)
        self.assertIn("1.01 x", text)
        self.assertIn("check buy <TICKER> <AMOUNT_JPY> <SECTOR>", text)
        self.assertNotIn(SENTINEL, text)
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_evidence_rejects_non_edinet_code(self):
        with self.assertRaises(SystemExit):
            build_evidence("7203", asof="2026-06-18", derived_root=self.base / "data" / "derived")

    def test_research_layer_has_no_network_or_secret_imports(self):
        files = list((ROOT / "radar" / "research").glob("*.py"))
        text = "\n".join(p.read_text(encoding="utf-8") for p in files)
        for needle in ("urllib", "requests", "socket", "load_api_key", "_load_dotenv"):
            self.assertNotIn(needle, text)

    def test_llm_handoff_packet_is_bounded_and_local_only(self):
        packet = build_llm_handoff(asof="2026-06-18", derived_root=self.base / "data" / "derived")
        with tempfile.TemporaryDirectory() as od:
            res = write_llm_handoff(packet, outputs_root=Path(od))
            text = Path(res["md_path"]).read_text(encoding="utf-8")
            manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertNotIn(SENTINEL, text)
        self.assertIn("LICENSE_MATRIX E5", text)
        self.assertIn("J-Quants market context", text)
        self.assertIn("price_coverage", text)
        self.assertIn("valuation_coverage", text)
        self.assertIn("PER trailing median", text)
        self.assertIn("2,530 JPY", text)
        self.assertIn("12.65 x", text)
        self.assertIn("UNKNOWN / 不足", text)
        self.assertIn("discipline check 未通過", text)
        self.assertFalse(manifest["raw_body_included"])
        self.assertFalse(manifest["llm_api_called"])
        self.assertEqual(manifest["third_party_llm_gate"], "LICENSE_MATRIX_E5_J5_CONFIRMED_2026-06-20")
        self.assertTrue(manifest["analysis_cleared"])
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_cli_help_ok(self):
        for cmd in ("research-queue", "evidence", "llm-brief"):
            p = subprocess.run([sys.executable, "-m", "radar", cmd, "--help"],
                               cwd=str(ROOT), capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
