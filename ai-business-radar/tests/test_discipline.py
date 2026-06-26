import unittest

from radar.discipline import check
from radar.report import render_check


class DisciplineCoreTests(unittest.TestCase):
    def _cfg(self):
        return {
            "policy": {
                "satellite": {
                    "max_pct_per_name": 2.5,
                    "max_pct_per_sector": 5.0,
                    "max_pct_of_total": 10.0,
                    "min_names": 5,
                    "universe": "JP_individual",
                },
                "discipline": {
                    "chase_unrealized_pct": 0.25,
                    "averaging_down_pct": -0.25,
                },
            }
        }

    def test_name_cap_breach_rejects_add(self):
        portfolio = {
            "holdings": [
                {"kind": "cash", "currency": "JPY", "market_value_jpy": 9_800_000},
                {"kind": "individual_stock", "ticker": "7203", "sector": "Autos",
                 "market_value_jpy": 100_000, "cost_basis_jpy": 100_000},
            ]
        }
        verdict = check(portfolio, self._cfg(), "add 7203 200000")
        self.assertFalse(verdict["ok"])
        self.assertTrue(any("1銘柄上限" in b for b in verdict["breaches"]))

    def test_overheated_flag_is_hard_rejection_only_when_declared(self):
        portfolio = {"holdings": [{"kind": "cash", "currency": "JPY", "market_value_jpy": 2_000_000}]}
        ok = check(portfolio, self._cfg(), "buy 7203 10000 Autos")
        hot = check(portfolio, self._cfg(), "buy 7203 10000 Autos --overheated")
        self.assertTrue(ok["ok"])
        self.assertFalse(hot["ok"])
        self.assertTrue(any("過熱" in b for b in hot["breaches"]))

    def test_averaging_down_requires_thesis_and_powder(self):
        portfolio = {
            "holdings": [
                {"kind": "cash", "currency": "JPY", "market_value_jpy": 1_980_000},
                {"kind": "individual_stock", "ticker": "7203", "sector": "Autos",
                 "market_value_jpy": 20_000, "cost_basis_jpy": 40_000},
            ]
        }
        bad = check(portfolio, self._cfg(), "add 7203 10000")
        good = check(portfolio, self._cfg(), "add 7203 10000 --thesis-intact --powder")
        self.assertFalse(bad["ok"])
        self.assertTrue(any("ナンピン" in b for b in bad["breaches"]))
        self.assertTrue(good["ok"])
        self.assertTrue(any("ナンピン" in w for w in good["warnings"]))

    def test_render_check_has_disclaimer_and_no_candidate_language(self):
        portfolio = {"holdings": [{"kind": "cash", "currency": "JPY", "market_value_jpy": 2_000_000}]}
        verdict = check(portfolio, self._cfg(), "buy 7203 10000 Autos")
        text = render_check(verdict)
        self.assertIn("買え/売れの指示ではない", text)
        self.assertNotIn("buy_candidate", text)
        self.assertNotIn("ランキング", text)


if __name__ == "__main__":
    unittest.main()
