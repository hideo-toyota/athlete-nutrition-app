"""`radar daily-update` orchestration tests (no network, no LLM API)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.daily_update import render_daily_summary, run_daily_update
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = "RAW_SENTINEL_SHOULD_NOT_RENDER"


def _measured(value, status="CALCULATION", unit="ratio", fields=None):
    return {
        "value": value, "status": status, "unit": unit, "classification": "own",
        "formula_id": "x_v1", "source_fields": fields or [], "source_periods": ["current"],
        "raw_hash_normalized": "normalized-hash", "raw_hash_compressed": "compressed-hash", "note": None,
    }


def _write_doc(base: Path, code="E02367", asof="2026-06-18"):
    d = base / "data" / "derived" / "features" / "edinet_financials_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": "1", "feature_set": "edinet_financials_v1",
        "feature_registry_version": "1", "generated_at": "2026-06-18T00:00:00+00:00",
        "asof": asof, "provider": "edinet-db", "dataset": "financials",
        "edinet_code": code, "period": "annual",
        "input": {
            "raw_hash_normalized": "normalized-hash", "raw_hash_compressed": "compressed-hash",
            "available_at": "2026-06-10T15:33:00+09:00", "retrieved_at": "2026-06-18T00:00:00+00:00",
        },
        "source_snapshot": {"used_fields": {"current": {"revenue": {"value": SENTINEL}}}},
        "features": {
            "revenue_growth_yoy": _measured(0.12),
            "operating_margin": _measured(0.08),
            "net_margin": _measured(0.04),
            "roic_proxy": _measured(None, status="UNKNOWN", unit=None),
            "valuation_status": _measured(None, status="UNKNOWN", unit=None),
        },
    }
    (d / f"{code}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def _write_companies_raw(base: Path, asof="2026-06-18"):
    d = base / "data" / "raw" / "edinet-db" / "companies" / asof
    d.mkdir(parents=True, exist_ok=True)
    p = d / "companies_page-1_per-page-100.json"
    p.write_text(json.dumps({
        "data": [{
            "edinet_code": "E02367",
            "sec_code": "72030",
            "name_ja": SENTINEL,
            "industry": "輸送用機器",
            "listing_status": "listed",
            "accounting_standard": "JP",
        }]
    }, ensure_ascii=False), encoding="utf-8")
    p.with_suffix(p.suffix + ".meta.json").write_text(json.dumps({
        "provider": "edinet-db",
        "dataset": "companies",
        "retrieved_at": "2026-06-18T00:00:00+00:00",
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
        "entity": {"company_name": SENTINEL, "market": "プライム", "sector33": "輸送用機器"},
        "input": {"input_manifest_digest": "jq-digest"},
        "features": {
            "latest_close": _measured(2530, unit="JPY"),
            "latest_volume": _measured(1234000, unit="shares"),
            "return_20d": _measured(0.05),
            "return_60d": _measured(-0.02),
            "return_252d": _measured(0.12),
            "dividend_record_present": _measured(True, unit="bool"),
        },
        "source_dates": {"latest_price_date": "2026-06-18"},
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
            "latest_price_date": "2026-06-18",
            "price_coverage_ratio": 1.0,
            "summary_coverage_ratio": 1.0,
        },
        "distribution": {
            "return_20d": {"count": 1, "median": 0.05, "positive_rate": 1.0},
            "return_60d": {"count": 1, "median": -0.02, "positive_rate": 0.0},
            "return_252d": {"count": 1, "median": 0.12, "positive_rate": 1.0},
        },
    }, ensure_ascii=False, sort_keys=True), encoding="utf-8")


class DailyUpdateDryRunTests(unittest.TestCase):
    def test_dry_run_touches_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            result = run_daily_update(asof="2026-06-18", dry_run=True, root=base,
                                      derived_root=base / "data" / "derived",
                                      outputs_root=base / "outputs")
            # dry-run plans, but writes nothing
            self.assertTrue(result["dry_run"])
            self.assertFalse((base / "outputs").exists())
            names = {s.name: s.status for s in result["steps"]}
            self.assertEqual(names["license-gate"], "done")
            self.assertIn(names["research-queue"], {"planned"})

    def test_summary_has_no_forbidden_terms(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            result = run_daily_update(asof="2026-06-18", dry_run=True, root=base)
            text = render_daily_summary(result)
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)
        self.assertIn("2026-06-20", text)  # gate confirmation date is surfaced

    def test_missing_data_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            result = run_daily_update(asof="2026-06-18", root=base,
                                      derived_root=base / "data" / "derived",
                                      outputs_root=base / "outputs")
        statuses = {s.name: s.status for s in result["steps"]}
        self.assertEqual(statuses["build-features(edinet)"], "skipped")
        self.assertEqual(statuses["build-company-map(edinet)"], "skipped")
        self.assertEqual(statuses["build-features(jquants)"], "skipped")
        self.assertNotIn("failed", set(statuses.values()))


class DailyUpdatePipelineTests(unittest.TestCase):
    def test_research_and_brief_built_and_clean(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_doc(base)
            result = run_daily_update(
                asof="2026-06-18", root=base,
                build_edinet=False, build_jquants=False,  # raw not present; use prebuilt derived
                derived_root=base / "data" / "derived",
                outputs_root=base / "outputs",
            )
            statuses = {s.name: s.status for s in result["steps"]}
            self.assertEqual(statuses["research-queue"], "done")
            self.assertEqual(statuses["llm-brief"], "done")
            self.assertEqual(result["summary"]["item_count"], 1)
            brief = Path(result["outputs"]["brief_md"])
            self.assertTrue(brief.exists())
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn(SENTINEL, text)
            self.assertIn("LICENSE_MATRIX E5", text)
            for token in FORBIDDEN_OUTPUT_TOKENS:
                self.assertNotIn(token, text)
            summary = render_daily_summary(result)
            self.assertIn(str(brief), summary)
            self.assertNotIn(SENTINEL, summary)

    def test_brief_manifest_marks_gate_confirmed(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_doc(base)
            run_daily_update(
                asof="2026-06-18", root=base, build_edinet=False, build_jquants=False,
                derived_root=base / "data" / "derived", outputs_root=base / "outputs",
            )
            manifest = json.loads((base / "outputs" / "llm_handoff" / "2026-06-18.json").read_text("utf-8"))
        self.assertFalse(manifest["llm_api_called"])
        self.assertFalse(manifest["raw_body_included"])
        self.assertTrue(manifest["analysis_cleared"])

    def test_daily_update_builds_company_map_and_routes_jquants_price_to_brief(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_doc(base)
            _write_companies_raw(base)
            _write_jquants(base)
            result = run_daily_update(
                asof="2026-06-18", root=base,
                build_edinet=True, build_jquants=False,
                derived_root=base / "data" / "derived", outputs_root=base / "outputs",
            )
            statuses = {s.name: s.status for s in result["steps"]}
            self.assertEqual(statuses["build-company-map(edinet)"], "done")
            self.assertEqual(statuses["research-queue"], "done")
            self.assertEqual(statuses["llm-brief"], "done")
            self.assertEqual(result["summary"]["jquants_context_status"], "CALCULATION")
            self.assertEqual(result["summary"]["jquants_latest_price_date"], "2026-06-18")
            brief = Path(result["outputs"]["brief_md"])
            text = brief.read_text(encoding="utf-8")
            self.assertIn("J-Quants market context", text)
            self.assertIn("J-Quants market/price context", text)
            self.assertIn("2,530 JPY", text)
            self.assertIn("72030", text)
            self.assertNotIn(SENTINEL, text)
            for token in FORBIDDEN_OUTPUT_TOKENS:
                self.assertNotIn(token, text)
            summary = render_daily_summary(result)
            self.assertIn("J-Quants 市場コンテキスト: CALCULATION", summary)
            self.assertIn("latest_price_date=2026-06-18", summary)


class DailyUpdateCliTests(unittest.TestCase):
    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "daily-update", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_cli_dry_run_runs(self):
        p = subprocess.run([sys.executable, "-m", "radar", "daily-update", "--dry-run",
                            "--asof", "2026-06-18"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Daily Update", p.stdout)
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, p.stdout)


if __name__ == "__main__":
    unittest.main()
