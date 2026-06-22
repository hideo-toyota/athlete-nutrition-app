import json
import tempfile
import unittest
from pathlib import Path

from radar import journal


class JournalActionAwareScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_log = journal.LOG
        journal.LOG = Path(self.tmp.name) / "decision_log.jsonl"

    def tearDown(self):
        journal.LOG = self.old_log
        self.tmp.cleanup()

    def _decision(self, action, ticker="7203"):
        return {
            "ticker": ticker,
            "account": "test",
            "action": action,
            "rationale": "反証可能な判断のテスト",
            "prediction": {
                "claim": "horizonでDCA比較を検証する",
                "metric": "対象銘柄リターン - DCAベンチリターン",
                "threshold": "0%",
                "horizon": "2026-06-01",
            },
            "vs_discipline": "in_discipline",
            "override_reason": "",
            "size": {"amount_jpy": 0 if action == "pass" else 100000},
            "ref_price": 100.0,
            "benchmark_ref": 100.0,
            "emotion_note": "test",
            "sources": ["test"],
            "retrieved_at": "2026-01-01T00:00:00+09:00",
        }

    def _outcomes(self):
        return [
            json.loads(line)
            for line in journal.LOG.read_text(encoding="utf-8").splitlines()
            if json.loads(line).get("type") == "outcome"
        ]

    def test_buy_hits_when_asset_beats_dca(self):
        did = journal.append_decision(self._decision("buy_new"))
        res = journal.score_due({
            "7203": {"2026-06-01": 120.0},
            "BENCHMARK": {"2026-06-01": 110.0},
        }, asof="2026-06-02")
        self.assertEqual(res["scored"], [did])
        outcome = self._outcomes()[0]
        self.assertEqual(outcome["score_direction"], "long")
        self.assertAlmostEqual(outcome["excess_vs_dca"], 0.10)
        self.assertAlmostEqual(outcome["decision_excess_vs_dca"], 0.10)
        self.assertTrue(outcome["hit"])

    def test_pass_hits_when_asset_lags_dca(self):
        did = journal.append_decision(self._decision("pass"))
        res = journal.score_due({
            "7203": {"2026-06-01": 90.0},
            "BENCHMARK": {"2026-06-01": 110.0},
        }, asof="2026-06-02")
        self.assertEqual(res["scored"], [did])
        outcome = self._outcomes()[0]
        self.assertEqual(outcome["score_direction"], "avoid")
        self.assertAlmostEqual(outcome["excess_vs_dca"], -0.20)
        self.assertAlmostEqual(outcome["decision_excess_vs_dca"], 0.20)
        self.assertTrue(outcome["hit"])

    def test_pass_misses_when_asset_beats_dca(self):
        journal.append_decision(self._decision("pass"))
        journal.score_due({
            "7203": {"2026-06-01": 120.0},
            "BENCHMARK": {"2026-06-01": 110.0},
        }, asof="2026-06-02")
        outcome = self._outcomes()[0]
        self.assertEqual(outcome["score_direction"], "avoid")
        self.assertAlmostEqual(outcome["excess_vs_dca"], 0.10)
        self.assertAlmostEqual(outcome["decision_excess_vs_dca"], -0.10)
        self.assertFalse(outcome["hit"])

    def test_review_aggregates_decision_adjusted_excess(self):
        journal.append_decision(self._decision("buy_new", ticker="AAA"))
        journal.append_decision(self._decision("pass", ticker="BBB"))
        journal.score_due({
            "AAA": {"2026-06-01": 120.0},
            "BBB": {"2026-06-01": 90.0},
            "BENCHMARK": {"2026-06-01": 110.0},
        }, asof="2026-06-02")
        rev = journal.review()
        self.assertEqual(rev["n_scored"], 2)
        self.assertEqual(rev["overall"]["hit_rate"], 1.0)
        self.assertAlmostEqual(rev["overall"]["avg_excess_vs_dca"], 0.15)
        self.assertAlmostEqual(rev["overall"]["avg_raw_excess_vs_dca"], -0.05)

    def test_outcome_rejects_bad_score_direction(self):
        journal.LOG.write_text(
            json.dumps({
                "type": "outcome",
                "id": "x",
                "excess_vs_dca": 0.1,
                "decision_excess_vs_dca": 0.1,
                "score_direction": "sideways",
                "hit": True,
            }) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(SystemExit):
            journal.review()


if __name__ == "__main__":
    unittest.main()
