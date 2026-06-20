"""J-Quants point-in-time price evidence + brief integration tests (no network/LLM)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.daily_update import run_daily_update
from radar.research import build_jquants_evidence, build_llm_handoff, render_jquants_evidence, write_llm_handoff
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent


def _m(value, unit, status=None):
    if value is None:
        status = "UNKNOWN"
    return {"value": value, "status": status or "CALCULATION", "unit": unit,
            "classification": "own", "note": None}


def _write_jquants(base: Path, code="72030", asof="2026-06-18", close=1234.0):
    d = base / "data" / "derived" / "features" / "jquants_equity_v1" / asof
    d.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema_version": "1", "feature_set": "jquants_equity_v1",
        "feature_registry_version": "1", "generated_at": "2026-06-18T00:00:00+00:00",
        "asof": asof, "provider": "jquants", "dataset": "bulk:master+prices+financials+dividends",
        "securities_code": code,
        "entity": {"company_name": "テスト自動車", "market": "プライム", "sector33": "輸送用機器",
                   "margin_type": "x", "master_date": asof},
        "input": {"raw_root": "x", "input_manifest_digest": "x", "normalization_version": "1"},
        "features": {
            "latest_close": _m(close, "JPY"),
            "latest_volume": _m(10000, "shares"),
            "return_20d": _m(0.05, "ratio"),
            "return_60d": _m(-0.02, "ratio"),
            "return_252d": _m(0.30, "ratio"),
            "sales_growth_yoy": _m(0.12, "ratio"),
            "operating_margin": _m(0.08, "ratio"),
            "net_margin": _m(0.04, "ratio"),
            "roe_proxy": _m(0.10, "ratio"),
            "equity_ratio": _m(0.40, "ratio"),
            "eps_trailing": _m(80.0, "JPY"),
            "bps": _m(700.0, "JPY"),
            "per_trailing": _m(15.43, "x"),
            "pbr": _m(1.76, "x"),
            "dividend_record_present": _m(True, "bool", status="CALCULATION"),
        },
        "source_dates": {"latest_price_date": "2026-06-17",
                         "latest_financial_disclosure_date": "2026-05-10",
                         "latest_dividend_pub_date": "2026-05-10"},
        "warnings": ["not_a_recommendation"],
    }
    (d / "features.jsonl").write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    return base / "data" / "derived"


class JquantsEvidenceTests(unittest.TestCase):
    def test_four_digit_code_matches_five_digit_record(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            derived = _write_jquants(base, code="72030")
            ev = build_jquants_evidence("7203", asof="2026-06-18", derived_root=derived)
        text = render_jquants_evidence(ev)
        self.assertIn("当時の株価", text)
        self.assertIn("1,234 JPY", text)          # PIT adjusted close
        self.assertIn("2026-06-17", text)         # latest_price_date
        self.assertIn("テスト自動車", text)
        self.assertIn("バリュエーション", text)    # PER/PBR section
        self.assertIn("per_trailing", text)
        self.assertIn("15.43 x", text)            # trailing PER
        self.assertIn("1.76 x", text)             # PBR
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_unknown_code_raises(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            derived = _write_jquants(base)
            with self.assertRaises(SystemExit):
                build_jquants_evidence("9999", asof="2026-06-18", derived_root=derived)

    def test_invalid_code_rejected(self):
        with self.assertRaises(SystemExit):
            build_jquants_evidence("abc!", asof="2026-06-18")

    def test_brief_jquants_only_without_edinet(self):
        """No EDINET financials present; brief must still build from price alone."""
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            derived = _write_jquants(base)
            packet = build_llm_handoff(asof="2026-06-18", derived_root=derived, jquants_codes=["7203"])
            self.assertEqual(len(packet["queue"]["items"]), 0)
            self.assertEqual(len(packet["jquants_blocks"]), 1)
            with tempfile.TemporaryDirectory() as od:
                res = write_llm_handoff(packet, outputs_root=Path(od))
                text = Path(res["md_path"]).read_text(encoding="utf-8")
                manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertIn("J-Quants price evidence", text)
        self.assertIn("1,234 JPY", text)
        self.assertEqual(manifest["jquants_block_count"], 1)
        self.assertTrue(manifest["analysis_cleared"])
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, text)

    def test_daily_update_surfaces_price(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _write_jquants(base)
            result = run_daily_update(
                asof="2026-06-18", root=base,
                build_edinet=False, build_jquants=False, jquants_codes=["7203"],
                derived_root=base / "data" / "derived", outputs_root=base / "outputs",
            )
            self.assertEqual(result["summary"]["jquants_blocks"], 1)
            statuses = {s.name: s.status for s in result["steps"]}
            self.assertEqual(statuses["llm-brief"], "done")
            brief = Path(result["outputs"]["brief_md"]).read_text(encoding="utf-8")
            self.assertIn("当時の株価", brief)

    def test_research_layer_has_no_network_imports(self):
        files = list((ROOT / "radar" / "research").glob("*.py"))
        text = "\n".join(p.read_text(encoding="utf-8") for p in files)
        for needle in ("urllib", "requests", "socket", "load_api_key", "_load_dotenv"):
            self.assertNotIn(needle, text)

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "jquants-evidence", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
