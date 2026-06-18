"""target-check の純計算とCLIガードのオフラインテスト(TARGET_CHECK_SPEC §7 準拠)。"""
from __future__ import annotations

import io
import math
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from radar import target_check
from radar.report import render_target_check

ROOT = Path(__file__).resolve().parent.parent


class TestRequiredCAGR(unittest.TestCase):
    def test_known_values(self):
        # 10x の必要CAGR: 5y≈58.5% / 7y≈38.9% / 10y≈25.9%
        self.assertAlmostEqual(target_check.required_cagr(10, 5), 0.5849, places=3)
        self.assertAlmostEqual(target_check.required_cagr(10, 7), 0.3895, places=3)
        self.assertAlmostEqual(target_check.required_cagr(10, 10), 0.2589, places=3)

    def test_double_in_one_year(self):
        self.assertAlmostEqual(target_check.required_cagr(2, 1), 1.0, places=9)


class TestTax(unittest.TestCase):
    def test_full_taxable(self):
        # f=1, t=0.20315, M=10 → (10-0.20315)/(1-0.20315) ≈ 12.295
        g = target_check.gross_multiple_after_tax(10, 1.0, 0.20315)
        self.assertAlmostEqual(g, 12.295, places=2)

    def test_nisa_no_tax(self):
        # f=0(全NISA)→ G = M
        g = target_check.gross_multiple_after_tax(10, 0.0, 0.20315)
        self.assertAlmostEqual(g, 10.0, places=9)


class TestBlend(unittest.TestCase):
    def test_unreachable_blend(self):
        # 0.9コア横ばい + 0.1サテライト10x = 1.9x(10xには原理的に届かない)
        r = target_check.compute(10, 10, initial=8_000_000, core_w=0.9, sat_w=0.1)
        ex = [b for b in r["blend_examples"] if b["sat_mult"] == 10.0][0]
        self.assertAlmostEqual(ex["total_mult"], 1.9, places=9)
        # 全体10xに必要なコア倍率は非現実的に大きい
        self.assertGreater(r["core_needed_for_target"], 9.0)


class TestRecovery(unittest.TestCase):
    def test_recovery_needed(self):
        self.assertAlmostEqual(target_check.recovery_needed(50), 100.0, places=6)
        self.assertAlmostEqual(target_check.recovery_needed(20), 25.0, places=6)
        self.assertEqual(target_check.recovery_needed(100), float("inf"))


class TestLeverage(unittest.TestCase):
    def test_ruin_line(self):
        r = target_check.compute(10, 10, initial=8_000_000, leverage=2.0)
        self.assertAlmostEqual(r["leverage_ruin_drop_pct"], 50.0, places=6)

    def test_no_leverage_none(self):
        r = target_check.compute(10, 10, initial=8_000_000, leverage=1.0)
        self.assertIsNone(r["leverage_ruin_drop_pct"])


class TestDCA(unittest.TestCase):
    def test_contrib_lowers_required_rate(self):
        # 積立込みの必要rは、現資産だけの必要r以下になる(入金が効くほど下がる)
        r = target_check.compute(10, 10, initial=8_000_000, monthly=250_000)
        self.assertIsNotNone(r["r_with_contrib"])
        self.assertLessEqual(r["r_with_contrib"], r["r_no_contrib"] + 1e-9)

    def test_zero_monthly_matches_no_contrib(self):
        r = target_check.compute(10, 10, initial=8_000_000, monthly=0.0)
        self.assertAlmostEqual(r["r_with_contrib"], r["r_no_contrib"], places=3)


class TestValidation(unittest.TestCase):
    def test_multiple_le_one(self):
        with self.assertRaises(SystemExit):
            target_check.compute(1.0, 10, initial=8_000_000)
        with self.assertRaises(SystemExit):
            target_check.compute(0.5, 10, initial=8_000_000)

    def test_years_le_zero(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 0, initial=8_000_000)
        with self.assertRaises(SystemExit):
            target_check.compute(10, -3, initial=8_000_000)

    def test_initial_le_zero(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=0)
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=-100)

    def test_monthly_negative(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, monthly=-1)

    def test_taxable_frac_out_of_range(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, taxable_frac=1.5)
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, taxable_frac=-0.1)

    def test_tax_rate_out_of_range(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, tax_rate=1.0)
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, tax_rate=-0.1)

    def test_leverage_le_zero(self):
        with self.assertRaises(SystemExit):
            target_check.compute(10, 10, initial=8_000_000, leverage=0)

    def test_nan_inf_rejected(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(SystemExit):
                target_check.compute(bad, 10, initial=8_000_000)
            with self.assertRaises(SystemExit):
                target_check.compute(10, bad, initial=8_000_000)
            with self.assertRaises(SystemExit):
                target_check.compute(10, 10, initial=bad)

    def test_bool_rejected(self):
        with self.assertRaises(SystemExit):
            target_check.compute(True, 10, initial=8_000_000)


class TestDeterminism(unittest.TestCase):
    def test_repeatable(self):
        a = target_check.compute(10, 10, initial=8_000_000, monthly=200_000)
        b = target_check.compute(10, 10, initial=8_000_000, monthly=200_000)
        self.assertEqual(a, b)


class TestOutputSafety(unittest.TestCase):
    """出力に買い候補語・ランキング・予測・推奨が無いこと(CLAIMS: UNSAFE禁止)。"""

    def test_no_unsafe_language(self):
        r = target_check.compute(10, 10, initial=8_000_000, leverage=2.0,
                                 monthly=100_000, max_dd_pct=40)
        md = render_target_check(r)
        # 断定的な推奨/予測表現は一切出さない(肯定形)。
        forbidden = ["おすすめ", "買うべき", "買い候補", "上がる可能性が高い",
                     "ランキング", "必ず儲か", "買い推奨", "売り推奨"]
        for w in forbidden:
            self.assertNotIn(w, md, f"出力に禁止語が含まれています: {w}")
        # 推奨/利益保証/予測 は「〜ではありません」の否定文脈でのみ許容。
        for w in ("推奨", "利益保証", "売買指示"):
            for line in md.splitlines():
                if w in line:
                    self.assertIn("ではありません", line,
                                  f"'{w}' が否定免責以外で使われています: {line}")

    def test_has_disclaimer_and_conditions(self):
        r = target_check.compute(10, 10, initial=8_000_000)
        md = render_target_check(r)
        self.assertIn("投資助言ではありません", md)
        self.assertIn("予測", md)
        self.assertIn("必要条件", md)
        self.assertIn("破綻条件", md)


class TestNoNetworkImport(unittest.TestCase):
    """target_check は外部接続モジュールを import しない(純計算)。"""

    def test_pure_stdlib(self):
        src = (ROOT / "radar" / "target_check.py").read_text(encoding="utf-8")
        for banned in ("import requests", "urllib", "http", "socket", "jquants", "edinet"):
            self.assertNotIn(banned, src.lower())


class TestCLINonRegression(unittest.TestCase):
    """既存コマンドが import 後も生きていること(純加法的)。"""

    def test_dispatch_symbols_present(self):
        from radar import __main__ as m
        for name in ("cmd_mirror", "cmd_check", "cmd_log", "cmd_score",
                     "cmd_review", "cmd_data_check", "cmd_target_check"):
            self.assertTrue(hasattr(m, name), f"{name} が消えています")


class TestCLISubprocess(unittest.TestCase):
    """実CLIを subprocess で起動し、--help 展開や引数解釈の回帰を捕捉する
    (cmd_* の存在確認だけでは argparse の help 文字列バグ等を見逃すため)。"""

    def _run(self, *cli_args):
        import subprocess
        import sys
        return subprocess.run([sys.executable, "-m", "radar", *cli_args],
                              cwd=str(ROOT), capture_output=True, text=True)

    def test_all_subcommand_help_ok(self):
        # 各サブコマンドの --help が argparse の % 展開等で落ちないこと。
        for cmd in ("mirror", "check", "log", "score", "review",
                    "data-check", "target-check", "sync"):
            p = self._run(cmd, "--help")
            self.assertEqual(p.returncode, 0,
                             f"`radar {cmd} --help` が失敗: {p.stderr}")
        self.assertEqual(self._run("--help").returncode, 0)

    def test_target_check_runs(self):
        p = self._run("target-check", "--multiple", "10", "--years", "10")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("target check", p.stdout)

    def test_target_check_with_options(self):
        p = self._run("target-check", "--multiple", "10", "--years", "7",
                      "--monthly", "250000", "--leverage", "2", "--max-dd", "40",
                      "--asof", "2026-06-15")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_existing_commands_non_regression(self):
        self.assertEqual(self._run("mirror").returncode, 0)
        self.assertEqual(self._run("data-check", "--offline").returncode, 0)
        self.assertEqual(
            self._run("check", "buy", "7203", "100000", "Financials").returncode, 0)

    def test_target_check_rejects_bad_input(self):
        self.assertNotEqual(self._run("target-check", "--multiple", "1",
                                      "--years", "10").returncode, 0)
        self.assertNotEqual(self._run("target-check", "--multiple", "10",
                                      "--years", "0").returncode, 0)
        self.assertNotEqual(self._run("target-check", "--multiple", "10",
                                      "--years", "10", "--asof", "2026-13-40").returncode, 0)


if __name__ == "__main__":
    unittest.main()
