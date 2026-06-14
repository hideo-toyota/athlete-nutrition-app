"""A0 オフラインテスト(ネットワーク禁止)。`python3 -m unittest -q` で実行。

外部URLへ一切接続しない。APIキーが出力/例外に出ないこと、注入可能 fetch、
壊れJSON/HTTPエラーの fake 再現、provenance schema、書込先限定を検証。
"""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.sources import common, provenance

SECRET = "SECRET_TOKEN_abc123XYZ"


class FakeResp:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body


class A0Tests(unittest.TestCase):
    def setUp(self):
        for k in common.KEY_VARS:
            os.environ.pop(k, None)

    def tearDown(self):
        for k in common.KEY_VARS:
            os.environ.pop(k, None)

    # --- secrets / redact ---
    def test_missing_key_stops_without_value(self):
        with self.assertRaises(SystemExit) as cm:
            common.load_api_key("JQUANTS_API_KEY")
        self.assertNotIn(SECRET, str(cm.exception))

    def test_redact_hides_known_key(self):
        os.environ["JQUANTS_API_KEY"] = SECRET
        out = common.redact(f"sending {SECRET} now")
        self.assertNotIn(SECRET, out)
        self.assertIn("REDACTED", out)

    def test_redact_bearer(self):
        out = common.redact("Authorization: Bearer abc.def.ghi")
        self.assertNotIn("abc.def.ghi", out)

    def test_exception_does_not_leak_key(self):
        os.environ["JQUANTS_API_KEY"] = SECRET

        def client(ep, p):
            raise Exception(f"connect failed with token {SECRET}")

        with self.assertRaises(RuntimeError) as cm:
            common.fetch("jquants", "/x", {}, client=client)
        self.assertNotIn(SECRET, str(cm.exception))

    # --- no network by default ---
    def test_default_client_refuses_network(self):
        with self.assertRaises(SystemExit):
            common.fetch("jquants", "/x", {})

    # --- injectable client/clock + http errors ---
    def test_http_error_statuses(self):
        for st in (401, 403, 429, 500):
            with self.assertRaises(RuntimeError):
                common.fetch("jquants", "/x", {}, client=lambda e, p, s=st: FakeResp(s))

    def test_network_failure(self):
        def client(ep, p):
            raise OSError("connection refused")

        with self.assertRaises(RuntimeError):
            common.fetch("jquants", "/x", {}, client=client)

    def test_fetch_ok_with_injected_clock(self):
        clk = lambda: datetime(2026, 6, 14, tzinfo=timezone.utc)
        raw, meta = common.fetch("jquants", "/x", {"q": 1},
                                 client=lambda e, p: FakeResp(200, b'{"a":1}'), clock=clk)
        self.assertEqual(raw, b'{"a":1}')
        self.assertTrue(meta["retrieved_at"].startswith("2026-06-14"))
        self.assertEqual(meta["raw_hash_compressed"], common.hash_bytes(b'{"a":1}'))

    # --- json validation ---
    def test_broken_json_stops(self):
        with self.assertRaises(SystemExit):
            common.parse_json_dict(b"{not json")

    def test_non_dict_root_stops(self):
        with self.assertRaises(SystemExit):
            common.parse_json_dict(b"[1,2,3]")

    # --- hash stability ---
    def test_hash_stable(self):
        self.assertEqual(common.hash_bytes(b"same"), common.hash_bytes(b"same"))
        self.assertEqual(common.hash_bytes(b'{"a":1,"b":2}'),
                         common.hash_bytes(b'{"a":1,"b":2}'))

    def test_normalized_hash_is_key_order_stable(self):
        a = common.normalize_json_bytes(b'{"a":1,"b":2}')
        b = common.normalize_json_bytes(b'{"b":2,"a":1}')
        self.assertEqual(common.hash_bytes(a), common.hash_bytes(b))

    # --- provenance schema ---
    def test_provenance_has_all_required_keys(self):
        m = provenance.make_provenance(provider="jquants", dataset="prices")
        provenance.validate_provenance(m)
        for k in provenance.REQUIRED_FIELDS:
            self.assertIn(k, m)

    def test_available_at_requires_tz_datetime(self):
        m = provenance.make_provenance(provider="x", dataset="d", available_at="2026-06-12")
        with self.assertRaises(SystemExit):
            provenance.validate_provenance(m)
        m2 = provenance.make_provenance(provider="x", dataset="d",
                                        available_at="2026-06-12T09:00:00+09:00")
        provenance.validate_provenance(m2)

    # --- write scope: only the given metadata dir ---
    def test_fetch_log_writes_only_given_dir(self):
        with tempfile.TemporaryDirectory() as td:
            m = provenance.make_provenance(provider="jquants", dataset="prices")
            p = provenance.append_fetch_log(td, m)
            self.assertTrue(Path(p).exists())
            self.assertEqual(Path(p).parent.resolve(), Path(td).resolve())

    # --- non-regression: existing commands intact ---
    def test_existing_cli_commands_intact(self):
        import radar.__main__ as m
        for fn in ("cmd_mirror", "cmd_check", "cmd_log", "cmd_score", "cmd_review"):
            self.assertTrue(hasattr(m, fn), f"{fn} が消えている(非回帰違反)")
        self.assertTrue(hasattr(m, "cmd_data_check"))


if __name__ == "__main__":
    unittest.main()
