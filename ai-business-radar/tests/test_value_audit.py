"""value-audit(B5 Phase A)のオフラインテスト(SPEC §8 / PLAN §6)。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from argparse import Namespace
from pathlib import Path

from radar import value_audit as va
from radar import value_store as vs
from radar import __main__ as m
from radar.report import render_value_audit, render_value_review

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_THESIS = ROOT / "journal" / "value_thesis_input.example.json"

VA_CFG = {"annual_hurdle_pct": 10, "annualization_day_base": 365,
          "min_cycle_days": 45, "max_cycle_days": 200, "benchmark_index_ref": None}


# ---------------------------------------------------------------------------
# operator 真理表(§2.6.1)
# ---------------------------------------------------------------------------
class TestEvaluateCondition(unittest.TestCase):
    def _c(self, **kw):
        return kw

    def test_ge_boundary_tolerance(self):
        self.assertTrue(va.evaluate_condition(self._c(operator=">=", threshold=3.0), 3.0))
        self.assertFalse(va.evaluate_condition(self._c(operator=">=", threshold=3.0), 2.9))
        self.assertTrue(va.evaluate_condition(self._c(operator=">=", threshold=3.0, tolerance=0.2), 2.85))

    def test_gt_lt_le(self):
        self.assertFalse(va.evaluate_condition(self._c(operator=">", threshold=3.0), 3.0))
        self.assertTrue(va.evaluate_condition(self._c(operator="<", threshold=5.0), 4.9))
        self.assertTrue(va.evaluate_condition(self._c(operator="<=", threshold=5.0), 5.0))

    def test_eq_tolerance(self):
        self.assertTrue(va.evaluate_condition(self._c(operator="==", threshold=10.0, tolerance=0.5), 10.4))
        self.assertFalse(va.evaluate_condition(self._c(operator="==", threshold=10.0, tolerance=0.5), 10.6))

    def test_in_out_range(self):
        self.assertTrue(va.evaluate_condition(self._c(operator="in_range", threshold=[1.0, 2.0]), 2.0))
        self.assertFalse(va.evaluate_condition(self._c(operator="in_range", threshold=[1.0, 2.0]), 2.1))
        self.assertTrue(va.evaluate_condition(self._c(operator="out_of_range", threshold=[1.0, 2.0]), 2.1))
        self.assertFalse(va.evaluate_condition(self._c(operator="out_of_range", threshold=[1.0, 2.0]), 1.5))

    def test_qualitative_only_is_none(self):
        self.assertIsNone(va.evaluate_condition(self._c(operator=">=", threshold=1, qualitative_only=True), 5))

    def test_unknown_actual_is_none(self):
        self.assertIsNone(va.evaluate_condition(self._c(operator=">=", threshold=1.0), va.unknown()))
        self.assertIsNone(va.evaluate_condition(self._c(operator=">=", threshold=1.0), float("nan")))
        self.assertIsNone(va.evaluate_condition(self._c(operator=">=", threshold=1.0), float("inf")))
        self.assertIsNone(va.evaluate_condition(self._c(operator=">=", threshold=1.0), "x"))

    def test_type_mismatch_raises(self):
        with self.assertRaises(ValueError):
            va.evaluate_condition(self._c(operator=">=", threshold=[1, 2]), 1.0)
        with self.assertRaises(ValueError):
            va.evaluate_condition(self._c(operator="in_range", threshold=5.0), 1.0)
        with self.assertRaises(ValueError):
            va.evaluate_condition(self._c(operator="??", threshold=1.0), 1.0)


# ---------------------------------------------------------------------------
# リターン数理
# ---------------------------------------------------------------------------
class TestReturns(unittest.TestCase):
    def test_raw_return(self):
        self.assertAlmostEqual(va.raw_return(2800, 3100), 3100 / 2800 - 1, places=9)

    def test_raw_return_bad_entry(self):
        with self.assertRaises(ValueError):
            va.raw_return(0, 100)

    def test_annualize_in_range(self):
        m_ = va.annualize(0.10, 91, VA_CFG)
        self.assertEqual(m_["status"], va.CALCULATION)
        self.assertAlmostEqual(m_["value"], (1.10) ** (365 / 91) - 1, places=9)

    def test_annualize_out_of_range_unknown(self):
        self.assertEqual(va.annualize(0.10, 10, VA_CFG)["status"], va.UNKNOWN)   # 短すぎ
        self.assertEqual(va.annualize(0.10, 400, VA_CFG)["status"], va.UNKNOWN)  # 長すぎ
        self.assertIsNone(va.annualize(0.10, 10, VA_CFG)["value"])               # value は None(0でない)

    def test_vs_target(self):
        ann = va.annualize(0.10, 91, VA_CFG)
        self.assertTrue(va.vs_target(ann, 0.10)["value"])
        self.assertEqual(va.vs_target(va.unknown(), 0.10)["status"], va.UNKNOWN)


# ---------------------------------------------------------------------------
# 集計(UNKNOWN を分母に入れない / 対DCA=UNKNOWN)
# ---------------------------------------------------------------------------
class TestAggregate(unittest.TestCase):
    def test_unknown_not_counted(self):
        outcomes = [
            {"vs_target_10pct": va.measured(True, va.CALCULATION),
             "annualized_return": va.measured(0.5, va.CALCULATION),
             "beat_dca": va.unknown(), "max_drawdown_pct": va.unknown(),
             "checklist_result": [
                 {"matched": True, "qualitative_only": False, "actual": va.measured(1, va.CALCULATION)},  # 正式
                 {"matched": True, "qualitative_only": False, "actual": va.measured(1, va.ASSUMPTION)},    # 参考のみ
                 {"matched": None, "qualitative_only": False, "actual": va.unknown()},  # UNKNOWN→除外
                 {"matched": True, "qualitative_only": True, "actual": va.unknown()},   # 定性→除外
             ],
             "falsification_triggered": [{"metric": "op_margin"}]},
            {"vs_target_10pct": va.unknown(),  # 年率UNKNOWN→対10%分母外
             "annualized_return": va.unknown(),
             "beat_dca": va.unknown(), "max_drawdown_pct": va.unknown(),
             "checklist_result": [], "falsification_triggered": []},
        ]
        s = va.aggregate(outcomes, VA_CFG)
        self.assertEqual(s["n_scored"], 2)
        self.assertEqual(s["n_annualized_unknown"], 1)
        self.assertEqual(s["checklist_den"], 1)          # FACT/CALCULATION のみ正式分母
        self.assertEqual(s["checklist_match_rate"], 1.0)
        self.assertEqual(s["checklist_ref_den"], 1)      # ASSUMPTION は参考枠へ分離
        self.assertEqual(s["checklist_ref_rate"], 1.0)
        self.assertEqual(s["hit_10pct_den"], 1)          # 年率確定の1件のみ
        self.assertEqual(s["hit_10pct"], 1.0)
        self.assertEqual(s["hit_dca_den"], 0)            # Phase A: 対DCA は分母0
        self.assertIsNone(s["hit_dca"])                  # 率を出さない(負けにしない)
        self.assertEqual(s["falsification_outcomes"], 1)


# ---------------------------------------------------------------------------
# ticker / path safety(§2.5)
# ---------------------------------------------------------------------------
class TestTickerPath(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(vs.validate_ticker("7203"), "7203")
        self.assertEqual(vs.validate_ticker("BRK.B"), "BRK.B")

    def test_reject(self):
        for bad in (".", "..", "", "a/b", "a\\b", "../x", " 7203", "x" * 16, "全角", 123, None):
            with self.assertRaises(SystemExit):
                vs.validate_ticker(bad)

    def test_safe_output_path_reserved(self):
        for bad in ("", ".", ".."):
            with self.assertRaises(SystemExit):
                vs.safe_output_path(bad)

    def test_safe_output_path_under_dir(self):
        p = vs.safe_output_path("7203")
        self.assertEqual(p.parent, vs.VALUE_AUDIT_OUT.resolve())


# ---------------------------------------------------------------------------
# 仮説入力の検証(必須・禁止・anti_thesis ゲート)
# ---------------------------------------------------------------------------
class TestThesisInput(unittest.TestCase):
    def setUp(self):
        self.base = json.loads(EXAMPLE_THESIS.read_text(encoding="utf-8"))

    def _write(self, d):
        f = Path(tempfile.mkdtemp()) / "t.json"
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return f

    def test_example_is_valid(self):
        vs.load_thesis_input(self._write(self.base))  # 例が契約を満たす

    def test_missing_required(self):
        for k in ("cheapness_reason", "anti_thesis", "falsification", "next_earnings_checklist"):
            d = json.loads(json.dumps(self.base)); d.pop(k)
            with self.assertRaises(SystemExit):
                vs.load_thesis_input(self._write(d))

    def test_forbidden_field(self):
        d = json.loads(json.dumps(self.base)); d["buy_intent"] = True
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))
        d2 = json.loads(json.dumps(self.base)); d2["cheapness_reason"]["target_price"] = 3000
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d2))

    def test_anti_thesis_placeholder_rejected(self):
        d = json.loads(json.dumps(self.base)); d["anti_thesis"]["structural_risk_case"] = "..."
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))
        d2 = json.loads(json.dumps(self.base)); d2["anti_thesis"]["intensifies_if"] = ""
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d2))

    def test_bad_position_intent(self):
        d = json.loads(json.dumps(self.base)); d["position_intent"] = "buy"
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))

    def test_bad_operator(self):
        d = json.loads(json.dumps(self.base)); d["falsification"][0]["operator"] = "≦"
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))

    def test_snapshot_cycle_inconsistent(self):
        d = json.loads(json.dumps(self.base))
        d["cycle"]["start_available_at"] = "2026-05-09T15:30:00+09:00"  # snapshot と別日
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))

    def test_discipline_status_forced(self):
        d = json.loads(json.dumps(self.base)); d["discipline_status"] = "通過"
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))

    def test_source_must_be_manual(self):
        d = json.loads(json.dumps(self.base)); d["source"] = "sync:jquants"
        with self.assertRaises(SystemExit):
            vs.load_thesis_input(self._write(d))


# ---------------------------------------------------------------------------
# 閉ループ e2e + amends/supersedes + 冪等(temp に隔離)
# ---------------------------------------------------------------------------
class TestClosedLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # value_store のパスを temp に差し替え(実データを汚さない)
        self._save = {k: getattr(vs, k) for k in
                      ("JOURNAL", "THESIS_LOG", "OUTCOME_LOG", "VALUE_AUDIT_OUT")}
        vs.JOURNAL = self.tmp / "journal"
        vs.THESIS_LOG = vs.JOURNAL / "value_thesis.jsonl"
        vs.OUTCOME_LOG = vs.JOURNAL / "value_outcomes.jsonl"
        vs.VALUE_AUDIT_OUT = self.tmp / "outputs" / "value_audit"
        self._save_out = m.OUTPUTS
        m.OUTPUTS = self.tmp / "outputs"

    def tearDown(self):
        for k, v in self._save.items():
            setattr(vs, k, v)
        m.OUTPUTS = self._save_out

    def _register(self):
        m.cmd_value_audit_register(Namespace(ticker=None, from_file=str(EXAMPLE_THESIS), asof="2026-06-01"))
        return vs.read_theses()[-1]["thesis_id"]

    def _outcome_file(self, thesis_id, asof="2026-08-08", exitp=3100.0, amends=None,
                      entry_av="2026-05-11T15:30:00+09:00", exit_av="2026-08-07T15:30:00+09:00",
                      nea="2026-08-07T15:30:00+09:00", fname="o.json"):
        d = {"thesis_id": thesis_id, "next_earnings_available_at": nea,
             "price_basis": "manual_next_trading_close",
             "entry_price": 2800.0, "entry_price_date": "2026-05-11", "entry_price_available_at": entry_av,
             "exit_price": exitp, "exit_price_date": "2026-08-07", "exit_price_available_at": exit_av,
             "actuals": {"revenue_growth": 4.5, "op_margin": 7.5},
             "asof": asof, "source": "manual"}
        if amends:
            d["amends"] = amends
        f = self.tmp / fname
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return f

    def test_register_score_review(self):
        tid = self._register()
        self.assertTrue((vs.VALUE_AUDIT_OUT / "7203.md").exists())
        m.cmd_value_audit_score(Namespace(from_file=str(self._outcome_file(tid)), asof=None))
        outs = vs.read_outcomes()
        self.assertEqual(len(outs), 1)
        o = outs[0]
        self.assertEqual(o["annualized_return"]["status"], va.CALCULATION)  # 91日=範囲内
        self.assertTrue(o["vs_target_10pct"]["value"])
        self.assertEqual(o["beat_dca"]["status"], va.UNKNOWN)               # 対DCA=UNKNOWN
        self.assertEqual(o["falsification_triggered"], [])                  # op_margin 7.5 は <5 でない
        m.cmd_value_audit_review(Namespace(asof=None))
        md = (m.OUTPUTS / "value_audit_review.md").read_text(encoding="utf-8")
        self.assertIn("手入力仮定", md)
        self.assertIn("UNKNOWN(未算出)", md)

    def test_idempotent_score(self):
        tid = self._register()
        f = self._outcome_file(tid)
        m.cmd_value_audit_score(Namespace(from_file=str(f), asof=None))
        m.cmd_value_audit_score(Namespace(from_file=str(f), asof=None))  # 二度目
        self.assertEqual(len(vs.read_outcomes()), 1)                     # 重複追記しない

    def test_pending_not_scored(self):
        tid = self._register()
        # asof が次決算より前 → pending(採点しない)
        m.cmd_value_audit_score(Namespace(from_file=str(self._outcome_file(tid, asof="2026-07-01")), asof=None))
        self.assertEqual(len(vs.read_outcomes()), 0)

    def test_amends_outcome_preserves_original(self):
        tid = self._register()
        m.cmd_value_audit_score(Namespace(from_file=str(self._outcome_file(tid)), asof=None))
        first = vs.read_outcomes()[0]
        # 訂正: amends 付きで別 exit_price を追記 → 2件になり原本は不変
        m.cmd_value_audit_score(Namespace(
            from_file=str(self._outcome_file(tid, exitp=2500.0, amends=first["event_id"])), asof=None))
        outs = vs.read_outcomes()
        self.assertEqual(len(outs), 2)
        self.assertEqual(outs[0]["event_id"], first["event_id"])  # 原本不変

    def test_active_theses_supersede(self):
        tid = self._register()
        # 同じ thesis_id を supersede する新 thesis を直接追記
        base = json.loads(EXAMPLE_THESIS.read_text(encoding="utf-8"))
        new = dict(base); new["supersedes"] = tid
        vs.append_thesis(new, asof="2026-06-02")
        actives = vs.active_theses()
        active_ids = {t["thesis_id"] for t in actives}
        self.assertNotIn(tid, active_ids)  # 旧版は inactive

    def test_active_theses_invalid_amends_stops(self):
        self._register()
        base = json.loads(EXAMPLE_THESIS.read_text(encoding="utf-8"))
        bad = dict(base); bad["thesis_id"] = "zzz"; bad["amends"] = "nonexistent_event"
        vs.append_thesis(bad, asof="2026-06-02")
        with self.assertRaises(SystemExit):
            vs.active_theses()

    def _raw_thesis(self, **kw):
        rec = {"type": "research_item", "subtype": "value_audit", "event_id": uuid.uuid4().hex}
        rec.update(kw)
        vs._append_jsonl(vs.THESIS_LOG, rec)

    def test_active_theses_supersede_cycle_stops(self):
        self._raw_thesis(thesis_id="AAA", supersedes="BBB")
        self._raw_thesis(thesis_id="BBB", supersedes="AAA")  # 相互 supersede=循環
        with self.assertRaises(SystemExit):
            vs.active_theses()

    def test_outcome_amends_invalid_stops(self):
        tid = self._register()
        with self.assertRaises(SystemExit):
            vs.append_outcome({"thesis_id": tid, "amends": "nonexistent_outcome_event",
                               "cycle_start_available_at": "2026-05-08T15:30:00+09:00",
                               "next_earnings_available_at": "2026-08-07T15:30:00+09:00",
                               "asof": "2026-08-08"})

    def test_register_rejects_future_pit(self):
        # snapshot/cycle.start が asof より未来 → register 停止(PIT)
        with self.assertRaises(SystemExit):
            m.cmd_value_audit_register(Namespace(ticker=None, from_file=str(EXAMPLE_THESIS), asof="2026-05-01"))

    def test_score_rejects_future_entry_av(self):
        tid = self._register()
        f = self._outcome_file(tid, entry_av="2026-09-01T00:00:00+09:00")  # asof より未来
        with self.assertRaises(SystemExit):
            m.cmd_value_audit_score(Namespace(from_file=str(f), asof=None))

    def test_score_rejects_future_exit_av(self):
        tid = self._register()
        f = self._outcome_file(tid, exit_av="2026-09-01T00:00:00+09:00")  # asof より未来
        with self.assertRaises(SystemExit):
            m.cmd_value_audit_score(Namespace(from_file=str(f), asof=None))

    def test_score_rejects_exit_before_next_earnings(self):
        tid = self._register()
        f = self._outcome_file(tid, exit_av="2026-08-06T15:30:00+09:00")  # 次決算より前
        with self.assertRaises(SystemExit):
            m.cmd_value_audit_score(Namespace(from_file=str(f), asof=None))

    def test_phase_a_checklist_official_rate_none(self):
        # 手入力 actual は ASSUMPTION → 正式 checklist 分母0 → 率は None(参考のみ算出され得る)
        tid = self._register()
        m.cmd_value_audit_score(Namespace(from_file=str(self._outcome_file(tid)), asof=None))
        stats = va.aggregate(vs.read_outcomes(), VA_CFG)
        self.assertEqual(stats["checklist_den"], 0)
        self.assertIsNone(stats["checklist_match_rate"])
        self.assertGreaterEqual(stats["checklist_ref_den"], 1)

    def test_review_shows_anti_thesis_and_order(self):
        tid = self._register()
        m.cmd_value_audit_score(Namespace(from_file=str(self._outcome_file(tid)), asof=None))
        m.cmd_value_audit_review(Namespace(asof=None))
        md = (m.OUTPUTS / "value_audit_review.md").read_text(encoding="utf-8")
        self.assertIn("反対仮説", md)          # cheapness/anti_thesis セクション
        self.assertIn("構造劣化かも", md)
        # 表示順: 反証(§2)→ anti_thesis(§4)→ 対10%(§6)。hit率が先頭に出ない。
        self.assertLess(md.index("反証条件に触れた件数"), md.index("反対仮説"))
        self.assertLess(md.index("反対仮説"), md.index("対10%ハードル hit率"))


# ---------------------------------------------------------------------------
# 出力の語彙ガード(推奨/予測/買い候補が無い)
# ---------------------------------------------------------------------------
class TestOutputSafety(unittest.TestCase):
    def test_no_unsafe_language(self):
        base = json.loads(EXAMPLE_THESIS.read_text(encoding="utf-8"))
        md = render_value_audit(base)
        forbidden = ["おすすめ", "買うべき", "買い候補", "上がる可能性が高い", "割安だから買い",
                     "ランキング", "必ず儲か", "buy_candidate"]
        for w in forbidden:
            self.assertNotIn(w, md, f"出力に禁止語: {w}")
        self.assertIn("購入意思ではありません", md)
        self.assertIn("検証対象", md)
        self.assertIn("反証条件", md)

    def test_review_no_unsafe(self):
        stats = va.aggregate([], VA_CFG)
        md = render_value_review(stats, 0)
        for w in ("おすすめ", "買うべき", "ランキング", "買い候補"):
            self.assertNotIn(w, md)


# ---------------------------------------------------------------------------
# config value_audit ブロックの検証(NaN/inf を弾く)
# ---------------------------------------------------------------------------
class TestConfigValueAudit(unittest.TestCase):
    def _write_cfg(self, mutate):
        from radar import config as cfgmod  # noqa
        base = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        mutate(base.setdefault("value_audit", {}))
        f = Path(tempfile.mkdtemp()) / "config.json"
        f.write_text(json.dumps(base, allow_nan=True), encoding="utf-8")
        return f

    def test_nan_inf_rejected(self):
        from radar import config as cfgmod
        for bad in (float("nan"), float("inf"), float("-inf")):
            f = self._write_cfg(lambda va: va.__setitem__("annual_hurdle_pct", bad))
            with self.assertRaises(SystemExit):
                cfgmod.load_config(f)

    def test_valid_value_audit_ok(self):
        from radar import config as cfgmod
        f = self._write_cfg(lambda va: None)  # 既存の正常値のまま
        cfgmod.load_config(f)  # 例外なし


# ---------------------------------------------------------------------------
# CLI 非回帰 + --help(argparse % 回帰の検出)
# ---------------------------------------------------------------------------
class TestCLISubprocess(unittest.TestCase):
    def _run(self, *a):
        return subprocess.run([sys.executable, "-m", "radar", *a],
                              cwd=str(ROOT), capture_output=True, text=True)

    def test_help_ok(self):
        for args in (("value-audit", "--help"), ("value-audit", "register", "--help"),
                     ("value-audit", "score", "--help"), ("value-audit", "review", "--help")):
            p = self._run(*args)
            self.assertEqual(p.returncode, 0, f"{args} 失敗: {p.stderr}")

    def test_existing_non_regression(self):
        self.assertEqual(self._run("mirror").returncode, 0)
        self.assertEqual(self._run("target-check", "--multiple", "10", "--years", "10").returncode, 0)
        self.assertEqual(self._run("data-check", "--offline").returncode, 0)


if __name__ == "__main__":
    unittest.main()
