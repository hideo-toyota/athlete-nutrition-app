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
            "jquants": {"base_url": "https://api.jquants.com/v1", "ping_path": "/token/auth_refresh",
                        "auth": "query:refreshtoken", "key_var": "JQUANTS_API_KEY"},
            "edinet-db": {"base_url": "https://edinetdb.com/v1", "ping_path": "/companies",
                          "auth": "bearer", "key_var": "EDINETDB_API_KEY", "ping_params": {"limit": 1}},
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
        # 鍵は url(query)に入るが、戻り値(endpoint/error)には出ない
        self.assertNotIn(SECRET, str(res))
        self.assertEqual(res["endpoint"], "/token/auth_refresh")
        # 実際に鍵は送信先には乗る(疎通のため)が、結果には残さない設計
        self.assertIn(SECRET, captured["url"])

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

    # --- auth header building ---
    def test_bearer_header(self):
        cap = {}
        self._ping(lambda url, h: cap.update(h) or FakeResp(200, b'{"a":1}'))
        self.assertEqual(cap.get("Authorization"), "Bearer " + SECRET)


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
