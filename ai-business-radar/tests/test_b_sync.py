"""Phase B minimal sync tests(fake client・実ネットワーク無し)。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.sources import edinet_db, provenance

ROOT = Path(__file__).resolve().parent.parent
SECRET = "LEAKCHECK_SYNC_KEY_abc123"
BODY_SENTINEL = "BODY_SHOULD_ONLY_BE_IN_RAW_FILE"

CFG = {
    "data_layer": {
        "retry_max": 2,
        "backoff_base_sec": 0,
        "timeout_sec": 5,
        "max_response_bytes": 256,
        "daily_request_budget": 50,
        "providers": {
            "edinet-db": {
                "base_url": "https://edinetdb.jp/v1",
                "ping_path": "/companies",
                "auth": "x-api-key",
                "key_var": "EDINETDB_API_KEY",
                "plan_or_limit": "unknown-personal-plan",
                "datasets": {
                    "companies": {"path": "/companies"},
                    "financials": {"path": "/companies/{code}/financials"},
                },
            },
        },
    },
}


class FakeResp:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body


def _key(_name):
    return SECRET


def _clock():
    return datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)


def _raw():
    return json.dumps({"data": [{"edinet_code": "E02367", "name": BODY_SENTINEL}]},
                      ensure_ascii=False).encode("utf-8")


def _financials_raw(*, submit_date="2026-06-17 15:30:00", marker=BODY_SENTINEL):
    return json.dumps({
        "data": [{
            "edinet_code": "E02367",
            "submit_date": submit_date,
            "fiscal_year": 2026,
            "revenue": 123456,
            "marker": marker,
        }],
    }, ensure_ascii=False).encode("utf-8")


class SyncCompaniesTests(unittest.TestCase):
    def _sync(self, client, *, asof="2026-06-17", cfg=None):
        if getattr(self, "td", None) is not None:
            self.td.cleanup()
        self.td = tempfile.TemporaryDirectory()
        base = Path(self.td.name)
        return edinet_db.sync_companies(
            cfg or CFG,
            asof=asof,
            page=1,
            per_page=1,
            raw_root=base / "data" / "raw",
            metadata_dir=base / "data" / "metadata",
            http_client=client,
            clock=_clock,
            sleeper=lambda _s: None,
            key_getter=_key,
        )

    def tearDown(self):
        td = getattr(self, "td", None)
        if td is not None:
            td.cleanup()

    def test_success_writes_raw_sidecar_and_fetch_log_without_returning_body(self):
        captured = {}

        def client(url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp(200, _raw())

        res = self._sync(client)
        self.assertEqual(res["provider"], "edinet-db")
        self.assertEqual(res["dataset"], "companies")
        self.assertNotIn(SECRET, str(res))
        self.assertNotIn(BODY_SENTINEL, str(res))
        self.assertEqual(captured["headers"]["X-API-Key"], SECRET)
        self.assertNotIn(SECRET, captured["url"])

        raw_path = Path(res["raw_path"])
        self.assertTrue(raw_path.exists())
        self.assertIn("data/raw/edinet-db/companies/2026-06-17", raw_path.as_posix())
        self.assertIn(BODY_SENTINEL, raw_path.read_text(encoding="utf-8"))

        meta_path = Path(res["provenance_path"])
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        for k in provenance.REQUIRED_FIELDS:
            self.assertIn(k, meta)
        self.assertEqual(meta["provider"], "edinet-db")
        self.assertEqual(meta["dataset"], "companies")
        self.assertEqual(meta["plan_or_limit"], "unknown-personal-plan")
        self.assertEqual(meta["raw_hash_compressed"], res["raw_hash_compressed"])
        self.assertIsNotNone(datetime.fromisoformat(meta["available_at"]).tzinfo)
        self.assertIsNotNone(datetime.fromisoformat(meta["retrieved_at"]).tzinfo)

        fetch_log = Path(res["metadata_dir"]) / "fetch_log.jsonl"
        self.assertTrue(fetch_log.exists())
        self.assertEqual(len(fetch_log.read_text(encoding="utf-8").splitlines()), 1)

    def test_same_raw_has_same_hash(self):
        res1 = self._sync(lambda _u, _h: FakeResp(200, _raw()))
        res2 = edinet_db.sync_companies(
            CFG,
            asof="2026-06-17",
            page=1,
            per_page=1,
            raw_root=Path(self.td.name) / "data" / "raw",
            metadata_dir=Path(self.td.name) / "data" / "metadata",
            http_client=lambda _u, _h: FakeResp(200, _raw()),
            clock=_clock,
            sleeper=lambda _s: None,
            key_getter=_key,
        )
        self.assertEqual(res1["raw_hash_compressed"], res2["raw_hash_compressed"])
        self.assertEqual(res1["raw_hash_normalized"], res2["raw_hash_normalized"])

    def test_auth_errors_do_not_retry(self):
        for st in (401, 403):
            calls = {"n": 0}

            def client(_u, _h, st=st):
                calls["n"] += 1
                return FakeResp(st)

            with self.assertRaises(SystemExit):
                self._sync(client)
            self.assertEqual(calls["n"], 1)

    def test_429_retries_then_succeeds(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(429) if calls["n"] == 1 else FakeResp(200, _raw())

        res = self._sync(client)
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(calls["n"], 2)

    def test_5xx_exhausts_retries(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(503)

        with self.assertRaises(SystemExit):
            self._sync(client)
        self.assertEqual(calls["n"], CFG["data_layer"]["retry_max"] + 1)

    def test_retry_max_zero_single_attempt(self):
        cfg = {"data_layer": dict(CFG["data_layer"], retry_max=0)}
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(503)

        with self.assertRaises(SystemExit):
            self._sync(client, cfg=cfg)
        self.assertEqual(calls["n"], 1)

    def test_network_error_redacts_key(self):
        def client(url, _h):
            raise TimeoutError(f"timeout url={url} key={SECRET}")

        with self.assertRaises(SystemExit) as cm:
            self._sync(client)
        self.assertNotIn(SECRET, str(cm.exception))

    def test_broken_json_non_dict_and_huge_do_not_write_raw(self):
        cases = [
            FakeResp(200, b"{not json"),
            FakeResp(200, b"[1,2,3]"),
            FakeResp(200, b'{"x":"' + b"a" * 1000 + b'"}'),
        ]
        for resp in cases:
            with self.subTest(resp=resp.body[:10]):
                with self.assertRaises(SystemExit):
                    self._sync(lambda _u, _h, resp=resp: resp)
                base = Path(self.td.name) / "data" / "raw"
                self.assertFalse(any(base.rglob("*.json")) if base.exists() else False)

    def test_partial_success_empty_data_is_still_raw_response(self):
        res = self._sync(lambda _u, _h: FakeResp(200, b'{"data":[],"page":1}'))
        self.assertTrue(Path(res["raw_path"]).exists())

    def test_pit_future_available_at_rejected_without_writing(self):
        with self.assertRaises(SystemExit):
            self._sync(lambda _u, _h: FakeResp(200, _raw()), asof="2026-06-16")
        base = Path(self.td.name) / "data" / "raw"
        self.assertFalse(any(base.rglob("*.json")) if base.exists() else False)

    def test_bad_page_and_per_page_rejected(self):
        for kwargs in ({"page": 0, "per_page": 1}, {"page": 1, "per_page": 0}):
            with self.assertRaises(SystemExit):
                edinet_db.sync_companies(
                    CFG,
                    asof="2026-06-17",
                    raw_root=Path(tempfile.mkdtemp()) / "data" / "raw",
                    metadata_dir=Path(tempfile.mkdtemp()) / "data" / "metadata",
                    http_client=lambda _u, _h: FakeResp(200, _raw()),
                    clock=_clock,
                    sleeper=lambda _s: None,
                    key_getter=_key,
                    **kwargs,
                )

    def test_invalid_asof_rejected_as_system_exit(self):
        for asof in ("20260617", "2026-02", "2026-02-31", "", None):
            with self.subTest(asof=asof):
                with self.assertRaises(SystemExit):
                    edinet_db.sync_companies(
                        CFG,
                        asof=asof,
                        page=1,
                        per_page=1,
                        raw_root=Path(tempfile.mkdtemp()) / "data" / "raw",
                        metadata_dir=Path(tempfile.mkdtemp()) / "data" / "metadata",
                        http_client=lambda _u, _h: FakeResp(200, _raw()),
                        clock=_clock,
                        sleeper=lambda _s: None,
                        key_getter=_key,
                    )


class SyncFinancialsTests(unittest.TestCase):
    def _sync(self, client, *, asof="2026-06-17", code="E02367", years=1, period="annual", cfg=None):
        if getattr(self, "td", None) is not None:
            self.td.cleanup()
        self.td = tempfile.TemporaryDirectory()
        base = Path(self.td.name)
        return edinet_db.sync_financials(
            cfg or CFG,
            asof=asof,
            code=code,
            years=years,
            period=period,
            raw_root=base / "data" / "raw",
            metadata_dir=base / "data" / "metadata",
            http_client=client,
            clock=_clock,
            sleeper=lambda _s: None,
            key_getter=_key,
        )

    def tearDown(self):
        td = getattr(self, "td", None)
        if td is not None:
            td.cleanup()

    def test_success_writes_financials_raw_sidecar_without_returning_body(self):
        captured = {}

        def client(url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp(200, _financials_raw())

        res = self._sync(client)
        self.assertEqual(res["provider"], "edinet-db")
        self.assertEqual(res["dataset"], "financials")
        self.assertEqual(res["code"], "E02367")
        self.assertNotIn(SECRET, str(res))
        self.assertNotIn(BODY_SENTINEL, str(res))
        self.assertIn("/companies/E02367/financials", captured["url"])
        self.assertNotIn(SECRET, captured["url"])
        self.assertEqual(captured["headers"]["X-API-Key"], SECRET)

        raw_path = Path(res["raw_path"])
        self.assertTrue(raw_path.exists())
        self.assertIn("data/raw/edinet-db/financials/2026-06-17", raw_path.as_posix())
        self.assertEqual(raw_path.name, "E02367_period-annual_years-1.json")
        self.assertIn(BODY_SENTINEL, raw_path.read_text(encoding="utf-8"))

        meta = json.loads(Path(res["provenance_path"]).read_text(encoding="utf-8"))
        for k in provenance.REQUIRED_FIELDS:
            self.assertIn(k, meta)
        self.assertEqual(meta["dataset"], "financials")
        self.assertEqual(meta["edinet_code"], "E02367")
        self.assertEqual(meta["endpoint"], "/companies/E02367/financials")
        self.assertEqual(meta["params"], {"code": "E02367", "years": 1, "period": "annual"})
        self.assertEqual(meta["plan_or_limit"], "unknown-personal-plan")
        self.assertIn("+09:00", meta["available_at"])

        fetch_log = Path(res["metadata_dir"]) / "fetch_log.jsonl"
        self.assertTrue(fetch_log.exists())
        self.assertEqual(len(fetch_log.read_text(encoding="utf-8").splitlines()), 1)

    def test_future_submit_date_rejected_without_writing(self):
        with self.assertRaises(SystemExit):
            self._sync(lambda _u, _h: FakeResp(200, _financials_raw(submit_date="2026-06-18 00:00:00")))
        base = Path(self.td.name) / "data" / "raw"
        self.assertFalse(any(base.rglob("*.json")) if base.exists() else False)

    def test_financials_input_validation(self):
        for code in ("7203", "../E02367", "E1234", "", None):
            with self.subTest(code=code):
                with self.assertRaises(SystemExit):
                    self._sync(lambda _u, _h: FakeResp(200, _financials_raw()), code=code)
        for kwargs in ({"years": 0}, {"period": "monthly"}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(SystemExit):
                    self._sync(lambda _u, _h: FakeResp(200, _financials_raw()), **kwargs)

    def test_financials_same_raw_has_same_hash(self):
        res1 = self._sync(lambda _u, _h: FakeResp(200, _financials_raw()))
        res2 = edinet_db.sync_financials(
            CFG,
            asof="2026-06-17",
            code="E02367",
            raw_root=Path(self.td.name) / "data" / "raw",
            metadata_dir=Path(self.td.name) / "data" / "metadata",
            http_client=lambda _u, _h: FakeResp(200, _financials_raw()),
            clock=_clock,
            sleeper=lambda _s: None,
            key_getter=_key,
        )
        self.assertEqual(res1["raw_hash_compressed"], res2["raw_hash_compressed"])
        self.assertEqual(res1["raw_hash_normalized"], res2["raw_hash_normalized"])

    def test_financials_auth_errors_do_not_retry(self):
        for st in (401, 403):
            calls = {"n": 0}

            def client(_u, _h, st=st):
                calls["n"] += 1
                return FakeResp(st)

            with self.assertRaises(SystemExit):
                self._sync(client)
            self.assertEqual(calls["n"], 1)

    def test_financials_429_retries_then_succeeds(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(429) if calls["n"] == 1 else FakeResp(200, _financials_raw())

        res = self._sync(client)
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(calls["n"], 2)

    def test_financials_5xx_exhausts_retries(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(503)

        with self.assertRaises(SystemExit):
            self._sync(client)
        self.assertEqual(calls["n"], CFG["data_layer"]["retry_max"] + 1)

    def test_financials_retry_max_zero_single_attempt(self):
        cfg = {"data_layer": dict(CFG["data_layer"], retry_max=0)}
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(503)

        with self.assertRaises(SystemExit):
            self._sync(client, cfg=cfg)
        self.assertEqual(calls["n"], 1)

    def test_financials_network_error_redacts_key(self):
        def client(url, _h):
            raise TimeoutError(f"timeout url={url} key={SECRET}")

        with self.assertRaises(SystemExit) as cm:
            self._sync(client)
        self.assertNotIn(SECRET, str(cm.exception))

    def test_financials_broken_json_non_dict_and_huge_do_not_write_raw(self):
        cases = [
            FakeResp(200, b"{not json"),
            FakeResp(200, b"[1,2,3]"),
            FakeResp(200, b'{"x":"' + b"a" * 1000 + b'"}'),
        ]
        for resp in cases:
            with self.subTest(resp=resp.body[:10]):
                with self.assertRaises(SystemExit):
                    self._sync(lambda _u, _h, resp=resp: resp)
                base = Path(self.td.name) / "data" / "raw"
                self.assertFalse(any(base.rglob("*.json")) if base.exists() else False)


class SyncFinancialsBatchTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _batch(self, client, *, codes=None, offset=0, limit=2, cfg=None):
        return edinet_db.sync_financials_batch(
            cfg or CFG,
            asof="2026-06-17",
            codes=codes or ["E00001", "E00002", "E00003"],
            offset=offset,
            limit=limit,
            years=1,
            period="annual",
            raw_root=self.base / "data" / "raw",
            metadata_dir=self.base / "data" / "metadata",
            http_client=client,
            clock=_clock,
            sleeper=lambda _s: None,
            key_getter=_key,
        )

    def test_batch_offset_limit_writes_manifest_without_returning_body(self):
        calls = []

        def client(url, _h):
            calls.append(url)
            return FakeResp(200, _financials_raw(marker=BODY_SENTINEL))

        res = self._batch(client, offset=1, limit=2)
        self.assertEqual(res["selected_count"], 2)
        self.assertEqual(res["saved_count"], 2)
        self.assertEqual(res["failure_count"], 0)
        self.assertEqual(res["next_offset"], 3)
        self.assertEqual(len(calls), 2)
        self.assertIn("/companies/E00002/financials", calls[0])
        self.assertIn("/companies/E00003/financials", calls[1])
        self.assertNotIn(SECRET, str(res))
        self.assertNotIn(BODY_SENTINEL, str(res))

        manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["saved_count"], 2)
        self.assertNotIn(SECRET, json.dumps(manifest, ensure_ascii=False))
        self.assertNotIn(BODY_SENTINEL, json.dumps(manifest, ensure_ascii=False))
        for code in ("E00002", "E00003"):
            p = self.base / "data" / "raw" / "edinet-db" / "financials" / "2026-06-17" / f"{code}_period-annual_years-1.json"
            self.assertTrue(p.exists())
            self.assertIn(BODY_SENTINEL, p.read_text(encoding="utf-8"))

    def test_batch_skip_existing_validates_sidecar_and_uses_zero_http(self):
        first = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()), codes=["E00001"], limit=1)
        self.assertEqual(first["saved_count"], 1)
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(200, _financials_raw())

        second = self._batch(client, codes=["E00001"], limit=1)
        self.assertEqual(second["saved_count"], 0)
        self.assertEqual(second["skipped_existing_count"], 1)
        self.assertEqual(calls["n"], 0)

    def test_batch_corrupt_sidecar_does_not_skip_existing(self):
        first = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()), codes=["E00001"], limit=1)
        raw = self.base / "data" / "raw" / "edinet-db" / "financials" / "2026-06-17" / "E00001_period-annual_years-1.json"
        raw.with_suffix(raw.suffix + ".provenance.json").write_text("{broken", encoding="utf-8")
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(200, _financials_raw())

        second = self._batch(client, codes=["E00001"], limit=1)
        self.assertEqual(first["saved_count"], 1)
        self.assertEqual(second["saved_count"], 1)
        self.assertEqual(second["skipped_existing_count"], 0)
        self.assertEqual(calls["n"], 1)

    def test_batch_preflights_invalid_code_before_fetch(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(200, _financials_raw())

        with self.assertRaises(SystemExit):
            self._batch(client, codes=["E00001", "bad"], limit=2)
        self.assertEqual(calls["n"], 0)
        self.assertFalse((self.base / "data" / "raw").exists())

    def test_batch_duplicate_codes_are_reported_and_skipped_deterministically(self):
        res = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()),
                          codes=["E00001", "E00001", "E00002"], limit=2)
        self.assertEqual(res["input_code_count"], 3)
        self.assertEqual(res["unique_code_count"], 2)
        self.assertEqual(res["duplicate_count"], 1)
        manifest = json.loads(Path(res["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["duplicates_skipped"], ["E00001"])

    def test_batch_limit_above_budget_rejected_before_fetch(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            return FakeResp(200, _financials_raw())

        with self.assertRaises(SystemExit):
            self._batch(client, limit=CFG["data_layer"]["daily_request_budget"] + 1)
        self.assertEqual(calls["n"], 0)

    def test_batch_offset_beyond_codes_writes_empty_manifest_without_fetch(self):
        calls = {"n": 0}
        res = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()),
                          codes=["E00001"], offset=5, limit=2)
        self.assertEqual(res["selected_count"], 0)
        self.assertEqual(res["saved_count"], 0)
        self.assertEqual(res["next_offset"], 5)
        self.assertEqual(calls["n"], 0)
        self.assertTrue(Path(res["manifest_path"]).exists())

    def test_batch_failure_records_redacted_manifest_and_no_body(self):
        calls = {"n": 0}

        def client(_u, _h):
            calls["n"] += 1
            raise TimeoutError(f"timeout key={SECRET} body={BODY_SENTINEL}")

        res = self._batch(client, codes=["E00001"], limit=1)
        self.assertEqual(res["saved_count"], 0)
        self.assertEqual(res["failure_count"], 1)
        self.assertEqual(res["next_offset"], 0)
        self.assertEqual(res["retry_offset"], 0)
        # retry_max=2 means three actual attempts; all are counted against budget.
        self.assertEqual(res["total_attempts"], CFG["data_layer"]["retry_max"] + 1)
        manifest_text = Path(res["manifest_path"]).read_text(encoding="utf-8")
        self.assertNotIn(SECRET, manifest_text)
        self.assertNotIn(BODY_SENTINEL, manifest_text)
        self.assertFalse(any((self.base / "data" / "raw").rglob("*.json")))

    def test_batch_stops_at_first_failure_without_skipping_resume_offset(self):
        calls = []

        def client(url, _h):
            calls.append(url)
            if "/companies/E00002/financials" in url:
                return FakeResp(503)
            return FakeResp(200, _financials_raw())

        res = self._batch(client, codes=["E00001", "E00002", "E00003"], limit=3)
        self.assertEqual(res["saved_count"], 1)
        self.assertEqual(res["failure_count"], 1)
        self.assertEqual(res["next_offset"], 1)
        self.assertEqual(res["retry_offset"], 1)
        self.assertTrue(any("/companies/E00001/financials" in c for c in calls))
        self.assertTrue(any("/companies/E00002/financials" in c for c in calls))
        self.assertFalse(any("/companies/E00003/financials" in c for c in calls))

    def test_batch_budget_is_persisted_by_existing_manifest_for_same_asof(self):
        cfg = {"data_layer": dict(CFG["data_layer"], daily_request_budget=1)}
        first = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()),
                            codes=["E00001"], limit=1, cfg=cfg)
        self.assertEqual(first["saved_count"], 1)
        res = self._batch(lambda _u, _h: FakeResp(200, _financials_raw()),
                          codes=["E00001", "E00002"], offset=1, limit=1, cfg=cfg)
        self.assertEqual(res["prior_attempts_for_asof"], 1)
        self.assertEqual(res["saved_count"], 0)
        self.assertEqual(res["failure_count"], 1)
        self.assertEqual(res["next_offset"], 1)


class SyncCLITests(unittest.TestCase):
    def test_sync_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "sync", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("edinet-db", p.stdout)
        self.assertIn("financials", p.stdout)
        self.assertIn("--codes-file", p.stdout)
        self.assertIn("--offset", p.stdout)
        self.assertIn("--limit", p.stdout)

    def test_cmd_sync_rejects_scope_before_loading_config(self):
        import radar.__main__ as m

        class Args:
            provider = "jquants"
            dataset = "companies"
            asof = "2026-06-17"
            page = 1
            per_page = 1
            code = None
            codes_file = None
            offset = 0
            limit = None
            years = 1
            period = "annual"

        with self.assertRaises(SystemExit):
            m.cmd_sync(Args())

    def test_cmd_sync_financials_requires_code(self):
        import radar.__main__ as m

        class Args:
            provider = "edinet-db"
            dataset = "financials"
            asof = "2026-06-17"
            page = 1
            per_page = 1
            code = None
            codes_file = None
            offset = 0
            limit = None
            years = 1
            period = "annual"

        with self.assertRaises(SystemExit):
            m.cmd_sync(Args())

    def test_cmd_sync_rejects_dataset_irrelevant_options(self):
        import radar.__main__ as m

        class CompaniesArgs:
            provider = "edinet-db"
            dataset = "companies"
            asof = "2026-06-17"
            page = 1
            per_page = 1
            code = None
            codes_file = None
            offset = 0
            limit = None
            years = 2
            period = "annual"

        class FinancialsArgs:
            provider = "edinet-db"
            dataset = "financials"
            asof = "2026-06-17"
            page = 2
            per_page = edinet_db.DEFAULT_PER_PAGE
            code = "E02367"
            codes_file = None
            offset = 0
            limit = None
            years = 1
            period = "annual"

        with self.assertRaises(SystemExit):
            m.cmd_sync(CompaniesArgs())
        with self.assertRaises(SystemExit):
            m.cmd_sync(FinancialsArgs())

    def test_cmd_sync_rejects_code_and_codes_file_together(self):
        import radar.__main__ as m

        class Args:
            provider = "edinet-db"
            dataset = "financials"
            asof = "2026-06-17"
            page = 1
            per_page = edinet_db.DEFAULT_PER_PAGE
            code = "E02367"
            codes_file = "data/metadata/codes.txt"
            offset = 0
            limit = None
            years = 1
            period = "annual"

        with self.assertRaises(SystemExit):
            m.cmd_sync(Args())

    def test_codes_file_reader_accepts_metadata_file_and_rejects_sensitive_paths(self):
        import radar.__main__ as m
        meta = ROOT / "data" / "metadata"
        meta.mkdir(parents=True, exist_ok=True)
        p = meta / "test_codes_for_unit.txt"
        try:
            p.write_text("# comment\nedinet_code\nE00001\nE00001,E00001 Inc\n\n", encoding="utf-8")
            self.assertEqual(m._load_edinet_codes_file(str(p)), ["E00001", "E00001"])
        finally:
            if p.exists():
                p.unlink()
        with self.assertRaises(SystemExit):
            m._load_edinet_codes_file(str(ROOT / ".env"))

    def test_cmd_sync_rejects_batch_options_with_single_code(self):
        import radar.__main__ as m

        class Args:
            provider = "edinet-db"
            dataset = "financials"
            asof = "2026-06-17"
            page = 1
            per_page = edinet_db.DEFAULT_PER_PAGE
            code = "E02367"
            codes_file = None
            offset = 1
            limit = None
            years = 1
            period = "annual"

        with self.assertRaises(SystemExit):
            m.cmd_sync(Args())


if __name__ == "__main__":
    unittest.main()
