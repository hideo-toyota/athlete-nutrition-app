"""J-Quants bulk local feature tests(no network / no env / no advice)."""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.features.jquants_bulk import build_jquants_bulk_features

ROOT = Path(__file__).resolve().parent.parent
RAW_SENTINEL = "RAW_SENTINEL_SHOULD_NOT_BE_STDOUT"


def _write_gz(path: Path, header: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(str(row.get(h, "")) for h in header) + "\n")


def _clock():
    return datetime(2026, 6, 19, 0, 0, 0, tzinfo=timezone.utc)


def _fixture(root: Path):
    raw = root / "data" / "raw" / "jquants" / "bulk"
    _write_gz(
        raw / "equities/master/live/equities_master_20260618.csv.gz",
        ["Date", "Code", "CoName", "S33Nm", "MktNm", "MrgnNm", "ScaleCat"],
        [
            {"Date": "2026-06-18", "Code": "72030", "CoName": "A社", "S33Nm": "輸送用機器", "MktNm": "プライム", "MrgnNm": "貸借", "ScaleCat": "TOPIX Large70"},
            {"Date": "2026-06-18", "Code": "99990", "CoName": RAW_SENTINEL, "S33Nm": "情報通信", "MktNm": "グロース", "MrgnNm": "信用", "ScaleCat": "-"},
            {"Date": "2026-06-18", "Code": "130A0", "CoName": "英字コード", "S33Nm": "その他", "MktNm": "その他", "MrgnNm": "その他", "ScaleCat": "-"},
        ],
    )
    price_header = ["Date", "Code", "C", "AC", "Vo", "AVo"]
    price_rows = []
    for i in range(0, 253):
        day = f"2025-10-{(i % 28) + 1:02d}" if i < 120 else f"2026-06-{((i - 120) % 18) + 1:02d}"
        price_rows.append({"Date": day, "Code": "72030", "C": 100 + i, "AC": 100 + i, "Vo": 1000 + i, "AVo": 1000 + i})
    price_rows.append({"Date": "2026-06-18", "Code": "99990", "C": 50, "AC": 50, "Vo": 10, "AVo": 10})
    _write_gz(raw / "equities/bars/daily/premium/live/equities_bars_daily_20260618.csv.gz", price_header, price_rows)
    summary_header = ["DiscDate", "DiscTime", "Code", "DiscNo", "DocType", "CurPerType", "CurPerEn", "Sales", "OP", "NP", "Eq", "TA"]
    _write_gz(
        raw / "fins/summary/historical/2026/fins_summary_202606.csv.gz",
        summary_header,
        [
            {"DiscDate": "2025-06-01", "DiscTime": "15:00", "Code": "72030", "DiscNo": "1", "DocType": "FYFinancialStatements_Consolidated_JP", "CurPerType": "FY", "CurPerEn": "2025-03-31", "Sales": "1000", "OP": "80", "NP": "50", "Eq": "400", "TA": "2000"},
            {"DiscDate": "2026-06-01", "DiscTime": "15:00", "Code": "72030", "DiscNo": "2", "DocType": "FYFinancialStatements_Consolidated_JP", "CurPerType": "FY", "CurPerEn": "2026-03-31", "Sales": "1200", "OP": "120", "NP": "60", "Eq": "500", "TA": "2200"},
            {"DiscDate": "2026-06-01", "DiscTime": "15:00", "Code": "99990", "DiscNo": "3", "DocType": "FYFinancialStatements_Consolidated_JP", "CurPerType": "FY", "CurPerEn": "2026-03-31", "Sales": "0", "OP": "0", "NP": "0", "Eq": "0", "TA": "0"},
        ],
    )
    _write_gz(
        raw / "fins/dividend/live/fins_dividend_20260618.csv.gz",
        ["PubDate", "PubTime", "Code", "RefNo", "DivRate"],
        [{"PubDate": "2026-06-18", "PubTime": "15:00", "Code": "72030", "RefNo": "1", "DivRate": "30"}],
    )
    return raw


class JQuantsBulkFeatureTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.raw = _fixture(self.base)

    def tearDown(self):
        self.td.cleanup()

    def test_build_local_features_without_ranking_or_raw_stdout(self):
        res = build_jquants_bulk_features(
            asof="2026-06-18",
            raw_root=self.raw,
            derived_root=self.base / "data" / "derived",
            clock=_clock,
        )
        self.assertEqual(res["feature_rows"], 3)
        self.assertTrue(Path(res["features_path"]).exists())
        self.assertTrue(Path(res["manifest_path"]).exists())
        self.assertTrue(Path(res["summary_path"]).exists())
        lines = Path(res["features_path"]).read_text(encoding="utf-8").splitlines()
        docs = [json.loads(line) for line in lines]
        self.assertEqual([d["securities_code"] for d in docs], ["130A0", "72030", "99990"])
        first = docs[1]
        self.assertAlmostEqual(first["features"]["sales_growth_yoy"]["value"], 0.2)
        self.assertAlmostEqual(first["features"]["operating_margin"]["value"], 0.1)
        self.assertEqual(first["features"]["dividend_record_present"]["value"], True)
        self.assertEqual(first["features"]["return_20d"]["unit"], "ratio")
        summary = Path(res["summary_path"]).read_text(encoding="utf-8")
        self.assertIn("no recommendation", summary)
        self.assertNotIn("ranking", summary.lower().replace("no ranking", ""))

    def test_invalid_asof_and_missing_raw_are_rejected(self):
        with self.assertRaises(SystemExit):
            build_jquants_bulk_features(asof="2026-02", raw_root=self.raw, derived_root=self.base / "data" / "derived")
        with self.assertRaises(SystemExit):
            build_jquants_bulk_features(asof="2026-06-18", raw_root=self.base / "missing", derived_root=self.base / "data" / "derived")

    def test_cli_help_ok_and_feature_layer_has_no_network_or_env(self):
        p = subprocess.run([sys.executable, "-m", "radar", "build-jquants-features", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("J-Quants", p.stdout)
        text = (ROOT / "radar" / "features" / "jquants_bulk.py").read_text(encoding="utf-8")
        for needle in ("urllib", "requests", "socket", "load_api_key", "_load_dotenv"):
            self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()
