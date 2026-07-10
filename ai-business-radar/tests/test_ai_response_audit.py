"""AI response audit tests: local-only, bounded, no LLM API."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from radar.research import build_ai_response_audit, render_ai_response_audit, write_ai_response_audit
from radar.research.common import FORBIDDEN_OUTPUT_TOKENS

ROOT = Path(__file__).resolve().parent.parent


class AIResponseAuditTests(unittest.TestCase):
    def test_build_classifies_claims_and_adoption(self):
        text = "\n".join([
            "EDINET FACT と J-Quants CALCULATION ではPERが12倍です。",
            "過去20日リターンの分布ではセクター中央値より強いです。",
            "このため今後も強い可能性があります。",
            "結論として一部は採用できます。",
        ])
        audit = build_ai_response_audit(response_text=text, source_name="answer.md")
        classes = [c["evidence_class"] for c in audit["claim_audit"]["claims"]]
        self.assertIn("A", classes)
        self.assertIn("C", classes)
        self.assertIn("F", classes)
        self.assertEqual(len(audit["assumption_audit"]), 10)
        self.assertGreaterEqual(audit["adoption"]["level"], 2)

    def test_render_sanitizes_forbidden_source_phrases(self):
        text = "BUY 7203 now. target price is 3000. 根拠はありません。"
        audit = build_ai_response_audit(response_text=text, source_name="bad.md")
        self.assertEqual(audit["adoption"]["level"], 4)
        rendered = render_ai_response_audit(audit)
        self.assertIn("禁止表現", rendered)
        self.assertNotIn("BUY 7203", rendered)
        self.assertNotIn("target price", rendered.lower())
        for token in FORBIDDEN_OUTPUT_TOKENS:
            self.assertNotIn(token, rendered)

    def test_write_outputs_manifest_without_full_source(self):
        audit = build_ai_response_audit(
            response_text="J-Quants derived の price_date は 2026-06-18 です。",
            source_name="sample-answer.md",
        )
        with tempfile.TemporaryDirectory() as td:
            res = write_ai_response_audit(audit, outputs_root=Path(td), output_name="checked")
            md = Path(res["md_path"])
            js = Path(res["manifest_path"])
            self.assertTrue(md.exists())
            self.assertTrue(js.exists())
            manifest = json.loads(js.read_text(encoding="utf-8"))
        self.assertFalse(manifest["source_text_included"])
        self.assertFalse(manifest["llm_api_called"])
        self.assertEqual(res["weak_claim_count"], len(manifest["claim_audit"]["weak_claims"]))

    def test_cli_help_ok(self):
        p = subprocess.run(
            [sys.executable, "-m", "radar", "ai-audit", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
