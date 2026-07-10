"""EDINET companies derived map tests(no network / no env / no advice)."""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.features import build_edinet_company_map

ROOT = Path(__file__).resolve().parent.parent
RAW_SENTINEL = "COMPANY_RAW_SENTINEL_SHOULD_NOT_PRINT"


def _clock():
    return datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)


def _write_companies_raw(base: Path, *, asof="2026-06-18"):
    d = base / "data" / "raw" / "edinet-db" / "companies" / asof
    d.mkdir(parents=True, exist_ok=True)
    p = d / "companies_page-1_per-page-100.json"
    p.write_text(json.dumps({
        "data": [
            {
                "edinet_code": "E02367",
                "sec_code": "72030",
                "name": RAW_SENTINEL,
                "name_ja": RAW_SENTINEL,
                "industry": "輸送用機器",
                "listing_status": "listed",
                "accounting_standard": "JP",
            },
            {
                "edinet_code": "not-code",
                "sec_code": "bad",
                "name": "ignored",
            },
        ],
        "meta": {"pagination": {"page": 1}},
    }, ensure_ascii=False), encoding="utf-8")
    p.with_suffix(p.suffix + ".meta.json").write_text(json.dumps({
        "provider": "edinet-db",
        "dataset": "companies",
        "retrieved_at": "2026-06-18T00:00:00+00:00",
    }, ensure_ascii=False), encoding="utf-8")
    return d


class EdinetCompanyMapFeatureTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.raw_dir = _write_companies_raw(self.base)

    def tearDown(self):
        self.td.cleanup()

    def test_build_company_map_writes_identifier_mapping_without_stdout_body(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = build_edinet_company_map(
                raw_dir=self.raw_dir,
                asof="2026-06-18",
                raw_root=self.base / "data" / "raw",
                derived_root=self.base / "data" / "derived",
                clock=_clock,
            )
        self.assertNotIn(RAW_SENTINEL, buf.getvalue())
        self.assertEqual(res["row_count"], 1)
        self.assertEqual(res["mapped_securities_code_count"], 1)
        rows = Path(res["companies_path"]).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 1)
        row = json.loads(rows[0])
        self.assertEqual(row["feature_set"], "edinet_company_map_v1")
        self.assertEqual(row["edinet_code"], "E02367")
        self.assertEqual(row["securities_code"], "72030")
        manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["input_file_count"], 1)
        self.assertEqual(manifest["mapped_securities_code_count"], 1)

    def test_rejects_path_outside_companies_raw(self):
        with self.assertRaises(SystemExit):
            build_edinet_company_map(
                raw_dir=self.base,
                asof="2026-06-18",
                raw_root=self.base / "data" / "raw",
                derived_root=self.base / "data" / "derived",
            )

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "build-company-map", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("EDINET", p.stdout)


if __name__ == "__main__":
    unittest.main()
