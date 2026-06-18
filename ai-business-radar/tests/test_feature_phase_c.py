"""Phase C feature generation tests(no network / no env / no raw body output)."""
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

from radar.features import build_financial_features
from radar.features.compute import compute_financial_features
from radar.sources import common, provenance

ROOT = Path(__file__).resolve().parent.parent
BODY_SENTINEL = "RAW_BODY_SHOULD_NOT_BE_PRINTED"


def _rows(*, previous=True, revenue=1200, restated=False):
    prev = {
        "edinet_code": "E02367",
        "fiscal_year": 2024,
        "revenue": 1000,
        "operating_income": 90,
        "net_income": 50,
        "net_assets": 400,
        "total_assets": 1800,
        "operating_cash_flow": 120,
        "capital_expenditure": -40,
        "cash_and_deposits": 250,
        "interest_bearing_debt": 100,
    }
    cur = {
        "edinet_code": "E02367",
        "fiscal_year": 2025,
        "revenue": revenue,
        "operating_income": 120,
        "net_income": 60,
        "net_assets": 500,
        "total_assets": 2000,
        "operating_cash_flow": 180,
        "capital_expenditure": -50,
        "cash_and_deposits": 300,
        "interest_bearing_debt": 80,
        "marker": BODY_SENTINEL,
    }
    if restated:
        cur["restatement_flag"] = "訂正あり"
    return [prev, cur] if previous else [cur]


def _raw_bytes(obj=None):
    obj = obj or {"data": _rows()}
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def _write_raw(base: Path, raw_obj=None, *, asof="2026-06-18", available_at="2026-06-17T15:30:00+09:00",
               edinet_code="E02367", compressed_override=None, normalized_override=None):
    raw = _raw_bytes(raw_obj)
    raw_dir = base / "data" / "raw" / "edinet-db" / "financials" / asof
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / f"{edinet_code}_period-annual_years-2.json"
    raw_path.write_bytes(raw)
    meta = provenance.make_provenance(
        provider="edinet-db",
        dataset="financials",
        endpoint=f"/companies/{edinet_code}/financials",
        params={"code": edinet_code, "years": 2, "period": "annual"},
        retrieved_at="2026-06-18T00:00:00+00:00",
        raw_hash_compressed=compressed_override or common.hash_bytes(raw),
        raw_hash_normalized=normalized_override or common.hash_bytes(common.normalize_json_bytes(raw)),
        raw_size=len(raw),
        content_type="application/json",
        vendor_last_modified=None,
        available_at=available_at,
        edinet_code=edinet_code,
        source_url=f"https://edinetdb.jp/v1/companies/{edinet_code}/financials",
        license_scope="personal/local-temporary-cache/no-redistribution/no-raw-llm",
        plan_or_limit="test",
    )
    raw_path.with_suffix(raw_path.suffix + ".provenance.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return raw_path


def _clock():
    return datetime(2026, 6, 18, 1, 2, 3, tzinfo=timezone.utc)


class PureFeatureTests(unittest.TestCase):
    def test_compute_ratios_are_decimal_ratio_and_unknowns_are_not_zero(self):
        res = compute_financial_features(
            {"data": _rows()},
            raw_hashes={"raw_hash_compressed": "c", "raw_hash_normalized": "n"},
        )
        f = res["features"]
        self.assertAlmostEqual(f["revenue_growth_yoy"]["value"], 0.2)
        self.assertEqual(f["revenue_growth_yoy"]["unit"], "ratio")
        self.assertAlmostEqual(f["operating_margin"]["value"], 0.1)
        self.assertEqual(f["operating_margin"]["unit"], "ratio")
        self.assertLess(abs(f["operating_margin"]["value"]), 1)
        self.assertEqual(f["roic_proxy"]["status"], "UNKNOWN")
        self.assertIsNone(f["roic_proxy"]["value"])
        self.assertEqual(f["valuation_status"]["status"], "UNKNOWN")
        self.assertIsNone(f["valuation_status"]["value"])
        for m in f.values():
            self.assertEqual(m["raw_hash_compressed"], "c")
            self.assertEqual(m["raw_hash_normalized"], "n")

    def test_missing_previous_period_keeps_growth_and_roe_unknown(self):
        f = compute_financial_features({"data": _rows(previous=False)})["features"]
        self.assertEqual(f["revenue_growth_yoy"]["status"], "UNKNOWN")
        self.assertIsNone(f["revenue_growth_yoy"]["value"])
        self.assertEqual(f["roe_proxy"]["status"], "UNKNOWN")
        self.assertIsNone(f["roe_proxy"]["value"])

    def test_denominator_zero_nan_inf_non_numeric_are_unknown(self):
        for revenue in (0, float("nan"), float("inf"), "not-a-number"):
            with self.subTest(revenue=repr(revenue)):
                f = compute_financial_features({"data": _rows(revenue=revenue)})["features"]
                self.assertEqual(f["operating_margin"]["status"], "UNKNOWN")
                self.assertIsNone(f["operating_margin"]["value"])

    def test_alias_conflict_is_unknown(self):
        rows = _rows()
        rows[-1]["sales"] = rows[-1]["revenue"] + 1
        f = compute_financial_features({"data": rows})["features"]
        self.assertEqual(f["operating_margin"]["status"], "UNKNOWN")
        self.assertIn("alias_conflict", f["operating_margin"]["note"])

    def test_actual_edinet_style_cash_flow_and_debt_aliases(self):
        rows = _rows()
        cur = rows[-1]
        cur.pop("operating_cash_flow")
        cur.pop("capital_expenditure")
        cur.pop("cash_and_deposits")
        cur.pop("interest_bearing_debt")
        cur["cf_operating"] = 180
        cur["capex"] = -50
        cur["cash"] = 300
        cur["ibd_current"] = 30
        cur["ibd_noncurrent"] = 50
        f = compute_financial_features({"data": rows})["features"]
        self.assertEqual(f["fcf_proxy"]["status"], "CALCULATION")
        self.assertEqual(f["fcf_proxy"]["value"], 130)
        self.assertEqual(f["net_cash"]["status"], "CALCULATION")
        self.assertEqual(f["net_cash"]["value"], 220)
        self.assertEqual(f["net_cash"]["source_fields"], ["cash", "ibd_current", "ibd_noncurrent"])


class BuildFeatureTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _build(self, raw_path, *, asof="2026-06-18"):
        return build_financial_features(
            raw_path=raw_path,
            asof=asof,
            raw_root=self.base / "data" / "raw",
            derived_root=self.base / "data" / "derived",
            clock=_clock,
        )

    def test_build_writes_derived_with_hashes_snapshot_and_no_stdout_body(self):
        raw_path = _write_raw(self.base)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self._build(raw_path)
        self.assertNotIn(BODY_SENTINEL, buf.getvalue())
        out = Path(res["output_path"])
        self.assertTrue(out.exists())
        self.assertIn("data/derived/features/edinet_financials_v1/2026-06-18/E02367.json", out.as_posix())
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["feature_set"], "edinet_financials_v1")
        self.assertEqual(doc["edinet_code"], "E02367")
        self.assertEqual(doc["features"]["operating_margin"]["value"], 0.1)
        self.assertEqual(doc["features"]["operating_margin"]["unit"], "ratio")
        self.assertEqual(doc["features"]["operating_margin"]["raw_hash_compressed"], res["raw_hash_compressed"])
        self.assertEqual(doc["input"]["raw_hash_normalized"], res["raw_hash_normalized"])
        self.assertIn("used_fields", doc["source_snapshot"])
        self.assertNotIn(BODY_SENTINEL, json.dumps(doc["source_snapshot"], ensure_ascii=False))
        self.assertIn("config_hash", doc["build"])
        self.assertEqual(res["feature_count"], 9)
        self.assertGreaterEqual(res["unknown_count"], 2)

    def test_pit_future_available_at_rejected_without_writing(self):
        raw_path = _write_raw(self.base, available_at="2026-06-19T00:00:00+09:00")
        with self.assertRaises(SystemExit):
            self._build(raw_path)
        derived = self.base / "data" / "derived"
        self.assertFalse(any(derived.rglob("*.json")) if derived.exists() else False)

    def test_available_at_without_timezone_rejected(self):
        raw_path = _write_raw(self.base, available_at="2026-06-17T15:30:00")
        with self.assertRaises(SystemExit):
            self._build(raw_path)

    def test_both_hashes_are_checked(self):
        for kwargs in ({"compressed_override": "bad"}, {"normalized_override": "bad"}):
            with self.subTest(kwargs=kwargs):
                self.td.cleanup()
                self.setUp()
                raw_path = _write_raw(self.base, **kwargs)
                with self.assertRaises(SystemExit):
                    self._build(raw_path)
                derived = self.base / "data" / "derived"
                self.assertFalse(any(derived.rglob("*.json")) if derived.exists() else False)

    def test_raw_path_traversal_rejected(self):
        outside = self.base / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self._build(outside)

    def test_invalid_edinet_code_rejected_before_output_path(self):
        raw_path = _write_raw(self.base, edinet_code="E1234")
        with self.assertRaises(SystemExit):
            self._build(raw_path)
        derived = self.base / "data" / "derived"
        self.assertFalse(any(derived.rglob("*.json")) if derived.exists() else False)

    def test_restatement_flags_are_kept(self):
        raw_path = _write_raw(self.base, {"data": _rows(restated=True)})
        res = self._build(raw_path)
        doc = json.loads(Path(res["output_path"]).read_text(encoding="utf-8"))
        self.assertEqual(doc["restatement_flags"][0]["field"], "restatement_flag")


class FeatureCLITests(unittest.TestCase):
    def test_build_features_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "build-features", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("edinet-db", p.stdout)
        self.assertIn("financials", p.stdout)

    def test_feature_layer_has_no_network_or_env_imports(self):
        files = list((ROOT / "radar" / "features").glob("*.py"))
        text = "\n".join(p.read_text(encoding="utf-8") for p in files)
        for needle in ("urllib", "requests", "socket", "load_api_key", "_load_dotenv"):
            self.assertNotIn(needle, text)


if __name__ == "__main__":
    unittest.main()
