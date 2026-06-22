"""Tests for `radar doctor` local diagnostics."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.doctor import build_doctor_report, render_doctor_report, write_doctor_report

ROOT = Path(__file__).resolve().parent.parent
SECRET = "LEAKCHECK_DOCTOR_SECRET"


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True), encoding="utf-8")


class DoctorReportTests(unittest.TestCase):
    def test_env_presence_does_not_render_secret_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".env").write_text(
                f"JQUANTS_API_KEY={SECRET}\nEDINETDB_API_KEY={SECRET}\nEXTRA_TOKEN={SECRET}\n",
                encoding="utf-8",
            )
            report = build_doctor_report(root)
            text = render_doctor_report(report)
        self.assertNotIn(SECRET, text)
        self.assertIn("JQUANTS_API_KEY: SET", text)
        self.assertIn("EDINETDB_API_KEY: SET", text)
        self.assertIn("extra_env_lines: 1", text)
        self.assertNotIn("EXTRA_TOKEN", text)

    def test_data_freshness_warns_when_raw_is_newer_than_derived(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_json(root / "data/raw/edinet-db/financials/2026-06-22/E00001.json", {"ok": True})
            _write_json(root / "data/raw/edinet-db/financials/2026-06-22/E00001.json.meta.json", {"ok": True})
            _write_json(root / "data/raw/edinet-db/financials/2026-06-22/E00001.json.provenance.json", {"ok": True})
            _write_json(root / "data/derived/features/edinet_financials_v1/2026-06-20/E00001.json", {"ok": True})
            _write_json(root / "data/raw/edinet-db/companies/2026-06-22/companies_page-1.json", {"ok": True})
            (root / "data/derived/features/edinet_company_map_v1/2026-06-19").mkdir(parents=True)
            (root / "data/derived/features/edinet_company_map_v1/2026-06-19/companies.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            report = build_doctor_report(root)
            text = render_doctor_report(report)
        self.assertIn("edinet_features_stale", "\n".join(report["warnings"]))
        self.assertIn("company_map_stale", "\n".join(report["warnings"]))
        self.assertIn("raw edinet financials: asof=2026-06-22", text)
        self.assertIn("raw edinet financials: asof=2026-06-22 files=1", text)
        self.assertIn("derived edinet financials: asof=2026-06-20", text)

    def test_journal_empty_is_visible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = build_doctor_report(root)
            text = render_doctor_report(report)
        self.assertIn("decision_log_empty", "\n".join(report["warnings"]))
        self.assertIn("decisions: 0 / outcomes: 0", text)

    def test_jquants_coverage_and_audit_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "data/derived/features/jquants_equity_v1/2026-06-21"
            d.mkdir(parents=True)
            (d / "features.jsonl").write_text("{}\n{}\n", encoding="utf-8")
            _write_json(d / "manifest.json", {
                "coverage": {
                    "latest_price_date": "2026-06-18",
                    "price_coverage_ratio": 0.97,
                    "valuation_coverage_ratio": 0.84,
                }
            })
            _write_json(root / "outputs/data_quality_audit.json", {
                "asof": "2026-06-20",
                "cross_check": {
                    "cross_checked_items": 12,
                    "metrics": {
                        "a": {"mismatch_rate": 0.2, "calibration_signal": "review"},
                        "b": {"mismatch_rate": 0.1, "calibration_signal": "ok"},
                    },
                },
                "valuation": {"valuation_coverage_ratio": 0.84},
            })
            report = build_doctor_report(root)
            text = render_doctor_report(report)
        self.assertIn("J-Quants features rows: 2", text)
        self.assertIn("J-Quants price coverage: 97.0%", text)
        self.assertIn("valuation_coverage: 84.0%", text)
        self.assertIn("a: 20.0%", text)

    def test_write_report_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = build_doctor_report(root)
            path = write_doctor_report(report, root=root)
            self.assertEqual(path, root / "outputs" / "doctor.md")
            self.assertTrue(path.exists())


class DoctorCLITests(unittest.TestCase):
    def test_doctor_help(self):
        proc = subprocess.run(
            [sys.executable, "-m", "radar", "doctor", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ローカル診断", proc.stdout)


if __name__ == "__main__":
    unittest.main()
