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
                "datasets": {"companies": {"path": "/companies"}},
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


class SyncCLITests(unittest.TestCase):
    def test_sync_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "sync", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("edinet-db", p.stdout)

    def test_cmd_sync_rejects_scope_before_loading_config(self):
        import radar.__main__ as m

        class Args:
            provider = "jquants"
            dataset = "companies"
            asof = "2026-06-17"
            page = 1
            per_page = 1

        with self.assertRaises(SystemExit):
            m.cmd_sync(Args())


if __name__ == "__main__":
    unittest.main()
