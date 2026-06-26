import unittest

from radar import concentration, data


class ConcentrationCoreTests(unittest.TestCase):
    def _cfg(self):
        return {
            "policy": {
                "satellite": {
                    "max_pct_per_name": 2.5,
                    "max_pct_per_sector": 5.0,
                    "max_pct_of_total": 10.0,
                    "min_names": 5,
                }
            }
        }

    def test_lookthrough_combines_direct_and_index_exposure(self):
        old = concentration.load_index
        try:
            concentration.load_index = lambda ref: {
                "as_of": "2026-01-01",
                "top_holdings": {"AAA": 0.2},
                "sector_weights": {"US-Tech/AI": 1.0},
                "region_weights": {"US": 1.0},
                "currency_weights": {"USD": 1.0},
            }
            portfolio = {
                "as_of": "2026-01-02",
                "holdings": [
                    {"kind": "individual_stock", "ticker": "AAA", "sector": "Tech",
                     "region": "US", "currency": "USD", "market_value_jpy": 100_000},
                    {"kind": "index_fund", "ticker": "ACWI", "composition_ref": "indices/acwi.json",
                     "currency": "JPY", "market_value_jpy": 500_000},
                    {"kind": "cash", "currency": "JPY", "market_value_jpy": 400_000},
                ],
            }
            out = concentration.look_through(portfolio, self._cfg())
        finally:
            concentration.load_index = old

        by_name = out["lookthrough"]["by_name"]
        self.assertAlmostEqual(by_name["AAA"], 20.0)
        self.assertAlmostEqual(by_name["その他(指数・分散)"], 40.0)
        self.assertAlmostEqual(out["lookthrough"]["by_sector"]["US-Tech/AI"], 50.0)
        self.assertAlmostEqual(out["satellite"]["individual_pct"], 10.0)

    def test_future_index_asof_stops_instead_of_warning_only(self):
        old = concentration.load_index
        try:
            concentration.load_index = lambda ref: {
                "as_of": "2026-02-01",
                "top_holdings": {"AAA": 1.0},
                "sector_weights": {},
                "region_weights": {},
                "currency_weights": {},
            }
            portfolio = {
                "as_of": "2026-01-31",
                "holdings": [
                    {"kind": "index_fund", "ticker": "IDX", "composition_ref": "indices/acwi.json",
                     "currency": "JPY", "market_value_jpy": 100_000},
                ],
            }
            with self.assertRaises(SystemExit):
                concentration.look_through(portfolio, self._cfg())
        finally:
            concentration.load_index = old

    def test_load_index_rejects_path_traversal(self):
        with self.assertRaises(SystemExit):
            data.load_index("../portfolio.json")


if __name__ == "__main__":
    unittest.main()
