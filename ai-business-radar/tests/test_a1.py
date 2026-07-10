"""A1 軽量疎通テスト(fake client・実ネットワーク無し)。`python3 -m unittest -q`。

検証: 鍵値/本文が出力に漏れない、200/401/403/429/5xx/timeout/壊れJSON/非dict/巨大response、
retry、--live が無ければ接続しない、A0 非回帰。
"""
from __future__ import annotations

import contextlib
import io
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.sources import common, live

SECRET = "LEAKCHECK_REFRESH_TOKEN_zzz999"

CFG = {
    "data_layer": {
        "retry_max": 2, "backoff_base_sec": 0, "timeout_sec": 5,
        "max_response_bytes": 64, "daily_request_budget": 50,
        "providers": {
            "jquants": {"base_url": "https://api.jquants.com/v2", "ping_path": "/bulk/list",
                        "auth": "x-api-key", "key_var": "JQUANTS_API_KEY",
                        "ping_params": {"endpoint": "/markets/calendar"}},
            "edinet-db": {"base_url": "https://edinetdb.jp/v1", "ping_path": "/companies",
                          "auth": "x-api-key", "key_var": "EDINETDB_API_KEY",
                          "ping_params": {"per_page": 1}},
        },
    }
}

CLK = lambda: datetime(2026, 6, 17, tzinfo=timezone.utc)


class FakeResp:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body


def _key(_name):
    return SECRET  # 鍵取得を差し替え(実 .env を読まない)


class A1Tests(unittest.TestCase):
    def tearDown(self):
        for k in common.KEY_VARS:
            os.environ.pop(k, None)

    def _ping(self, client, provider="edinet-db"):
        return live.ping(provider, CFG, client=client, clock=CLK,
                         sleeper=lambda _s: None, key_getter=_key)

    def test_redact_refreshtoken_query_param(self):
        s = common.redact("https://api.example.test/ping?refreshtoken=abc123&x=1")
        self.assertNotIn("abc123", s)
        self.assertIn("refreshtoken=***REDACTED***", s)

    # --- success ---
    def test_success_200_dict(self):
        res = self._ping(lambda url, h: FakeResp(200, b'{"ok":true}'))
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], 200)
        self.assertEqual(res["endpoint"], "/companies")
        self.assertIsNone(res["error"])

    # --- key never leaks ---
    def test_key_not_in_result_or_endpoint(self):
        captured = {}

        def client(url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return FakeResp(200, b'{"ok":1}')

        res = self._ping(client, provider="jquants")
        # 鍵は送信用headerに入るが、戻り値(endpoint/error)には出ない
        self.assertNotIn(SECRET, str(res))
        self.assertEqual(res["endpoint"], "/bulk/list")
        self.assertIn(SECRET, str(captured["headers"]))
        self.assertNotIn(SECRET, captured["url"])

    def test_query_auth_url_exception_redacts_secret_without_env(self):
        cfg = {
            "data_layer": {
                "retry_max": 0, "backoff_base_sec": 0, "timeout_sec": 5,
                "max_response_bytes": 64, "daily_request_budget": 50,
                "providers": {
                    "jquants": {"base_url": "https://api.example.test", "ping_path": "/ping",
                                "auth": "query:refreshtoken", "key_var": "JQUANTS_API_KEY"},
                },
            }
        }

        def client(url, _headers):
            self.assertIn(SECRET, url)
            raise Exception(f"failed url={url}")

        res = live.ping("jquants", cfg, client=client, clock=CLK,
                        sleeper=lambda _s: None, key_getter=_key)
        self.assertFalse(res["success"])
        self.assertNotIn(SECRET, str(res))
        self.assertNotIn("refreshtoken=" + SECRET, str(res))

    def test_error_message_redacts_key(self):
        os.environ["EDINETDB_API_KEY"] = SECRET

        def client(url, headers):
            raise Exception(f"boom with {SECRET}")

        res = self._ping(client)
        self.assertFalse(res["success"])
        self.assertNotIn(SECRET, str(res))

    # --- http errors ---
    def test_auth_errors_no_retry(self):
        for st in (401, 403):
            calls = {"n": 0}

            def client(url, h, st=st, calls=calls):
                calls["n"] += 1
                return FakeResp(st)

            res = self._ping(client)
            self.assertFalse(res["success"])
            self.assertEqual(res["status"], st)
            self.assertEqual(calls["n"], 1)  # 401/403 は再試行しない

    def test_429_retries_then_succeeds(self):
        calls = {"n": 0}

        def client(url, h):
            calls["n"] += 1
            return FakeResp(429) if calls["n"] == 1 else FakeResp(200, b'{"ok":1}')

        res = self._ping(client)
        self.assertTrue(res["success"])
        self.assertEqual(res["attempts"], 2)

    def test_5xx_exhausts_retries(self):
        res = self._ping(lambda url, h: FakeResp(503))
        self.assertFalse(res["success"])
        self.assertEqual(res["status"], 503)
        self.assertEqual(res["attempts"], CFG["data_layer"]["retry_max"] + 1)

    def test_retry_max_zero_means_single_attempt(self):
        cfg = {
            "data_layer": dict(CFG["data_layer"], retry_max=0),
        }
        calls = {"n": 0}

        def client(url, h):
            calls["n"] += 1
            return FakeResp(503)

        res = live.ping("edinet-db", cfg, client=client, clock=CLK,
                        sleeper=lambda _s: None, key_getter=_key)
        self.assertFalse(res["success"])
        self.assertEqual(calls["n"], 1)
        self.assertEqual(res["attempts"], 1)

    # --- network failure / timeout ---
    def test_network_failure_redacted(self):
        def client(url, h):
            raise TimeoutError("connection timed out")

        res = self._ping(client)
        self.assertFalse(res["success"])
        self.assertIn("network error", res["error"])

    # --- broken / non-dict / huge ---
    def test_broken_json(self):
        res = self._ping(lambda url, h: FakeResp(200, b"{not json"))
        self.assertFalse(res["success"])

    def test_empty_body(self):
        res = self._ping(lambda url, h: FakeResp(200, b""))
        self.assertFalse(res["success"])

    def test_non_dict_root(self):
        res = self._ping(lambda url, h: FakeResp(200, b"[1,2,3]"))
        self.assertFalse(res["success"])

    def test_huge_response(self):
        big = b'{"x":"' + b"a" * 1000 + b'"}'  # > max_response_bytes(64)
        res = self._ping(lambda url, h: FakeResp(200, big))
        self.assertFalse(res["success"])

    # --- bad provider / missing config ---
    def test_unknown_provider(self):
        with self.assertRaises(SystemExit):
            live.ping("nasdaq", CFG, client=lambda u, h: FakeResp(200), key_getter=_key)

    def test_missing_provider_cfg(self):
        with self.assertRaises(SystemExit):
            live.ping("jquants", {"data_layer": {"providers": {}}},
                      client=lambda u, h: FakeResp(200), key_getter=_key)

    def test_config_allows_retry_zero_and_backoff_zero(self):
        from radar.config import _check_data_layer
        _check_data_layer({
            "retry_max": 0,
            "backoff_base_sec": 0,
            "timeout_sec": 1,
            "max_response_bytes": 1,
            "daily_request_budget": 1,
        })

    # --- auth header building ---
    def test_x_api_key_header(self):
        cap = {}
        self._ping(lambda url, h: cap.update(h) or FakeResp(200, b'{"a":1}'))
        self.assertEqual(cap.get("X-API-Key"), SECRET)


class DataCheckCLITests(unittest.TestCase):
    """cmd_data_check の分岐(--live 無しは接続しない・キー値漏れない)。"""

    def tearDown(self):
        for k in common.KEY_VARS:
            os.environ.pop(k, None)

    def test_live_requires_provider(self):
        import radar.__main__ as m
        with self.assertRaises(SystemExit):
            m.cmd_data_check(False, live=True, provider=None)

    def test_no_offline_no_live_does_not_connect(self):
        import radar.__main__ as m
        # 外部接続せず、案内して停止(従来の A0 非回帰: offline=False は SystemExit)
        with self.assertRaises(SystemExit):
            m.cmd_data_check(False)

    def test_offline_and_live_are_mutually_exclusive(self):
        import radar.__main__ as m
        with self.assertRaises(SystemExit):
            m.cmd_data_check(True, live=True, provider="edinet-db")

    def test_provider_requires_live(self):
        import radar.__main__ as m
        with self.assertRaises(SystemExit):
            m.cmd_data_check(True, live=False, provider="edinet-db")

    def test_offline_hides_key_value(self):
        import radar.__main__ as m
        os.environ["JQUANTS_API_KEY"] = "LEAKCHECK_XYZ"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            m.cmd_data_check(True)
        out = buf.getvalue()
        self.assertNotIn("LEAKCHECK_XYZ", out)
        self.assertIn("設定あり", out)


if __name__ == "__main__":
    unittest.main()
