"""J-Quants REST client security tests(no real network/env leakage)."""
from __future__ import annotations

import os
import unittest
from urllib.error import HTTPError, URLError

from radar.sources import common
from radar.sources.jquants_rest_client import JQuantsRestClient


class JQuantsRestClientSecurityTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = common._ENV
        common._ENV = common.ROOT / "__nonexistent_env_for_jquants_rest_tests__"
        self._old = {k: os.environ.get(k) for k in (
            "JQUANTS_API_KEY", "JQUANTS_REFRESH_TOKEN", "JQUANTS_MAILADDRESS",
            "JQUANTS_PASSWORD", "JQUANTS_ID_TOKEN",
        )}
        for k in self._old:
            os.environ.pop(k, None)

    def tearDown(self):
        common._ENV = self._env_backup
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_auth_refresh_http_error_redacts_refreshtoken_url(self):
        secret = "REFRESH_SECRET_123"
        os.environ["JQUANTS_REFRESH_TOKEN"] = secret

        def opener(url, headers, **kwargs):
            raise HTTPError(url, 401, "Unauthorized", hdrs=None, fp=None)

        c = JQuantsRestClient(opener=opener)
        with self.assertRaises(SystemExit) as cm:
            c.authenticate()
        msg = str(cm.exception)
        self.assertNotIn(secret, msg)
        self.assertNotIn("refreshtoken=" + secret, msg)
        self.assertNotIn("?", msg)

    def test_get_network_error_redacts_bearer_token(self):
        token = "ID_TOKEN_SECRET_456"

        def opener(url, headers, **kwargs):
            raise URLError("failed Authorization: Bearer " + token)

        c = JQuantsRestClient(opener=opener)
        c._id_token = token
        with self.assertRaises(SystemExit) as cm:
            c.daily_quotes(code="7203", date_from="2026-06-01", date_to="2026-06-02")
        msg = str(cm.exception)
        self.assertNotIn(token, msg)
        self.assertIn("REDACTED", msg)


if __name__ == "__main__":
    unittest.main()
