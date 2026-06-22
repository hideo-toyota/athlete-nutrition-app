"""J-Quants Bulk sync tests(fake client; no real network/env)."""
from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from radar.sources import jquants_bulk

ROOT = Path(__file__).resolve().parent.parent
SECRET = "LEAKCHECK_JQUANTS_BULK_SECRET"
BODY = b"Date,Code,C\n2026-06-22,72030,3000\n"


CFG = {
    "data_layer": {
        "timeout_sec": 5,
        "max_response_bytes": 4096,
        "providers": {
            "jquants": {
                "base_url": "https://api.jquants.example/v2",
                "key_var": "JQUANTS_API_KEY",
                "plan_or_limit": "test-plan",
            },
        },
    },
}


def _key(_name):
    return SECRET


def _clock():
    return datetime(2026, 6, 23, 0, 0, tzinfo=timezone.utc)


def _gz_bytes(payload: bytes = BODY) -> bytes:
    return gzip.compress(payload)


class JQuantsBulkSyncTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.raw = self.base / "data" / "raw" / "jquants" / "bulk"
        self.meta = self.base / "data" / "metadata"

    def tearDown(self):
        self.td.cleanup()

    def _json_getter(self, url, headers, *, timeout, max_bytes):
        self.assertEqual(headers.get("X-API-Key"), SECRET)
        self.assertNotIn(SECRET, url)
        if url.startswith("https://api.jquants.example/v2/bulk/list"):
            return {
                "data": [
                    {
                        "Key": "equities/bars/daily/premium/live/equities_bars_daily_20260622.csv.gz",
                        "LastModified": "2026-06-23T01:00:00+00:00",
                        "Size": len(_gz_bytes()),
                    }
                ]
            }
        if url.startswith("https://api.jquants.example/v2/bulk/get"):
            return {"data": {"url": "https://download.example/file.csv.gz?token=" + SECRET}}
        raise AssertionError(url)

    def _downloader(self, url, dest, *, timeout):
        self.assertIn(SECRET, url)  # download URL may contain opaque token, but must not be persisted.
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_gz_bytes())

    def test_download_bulk_raw_and_manifest_without_secret_or_download_url(self):
        res = jquants_bulk.fetch_bulk(
            CFG,
            endpoints=["/equities/bars/daily"],
            from_date="2026-06-22",
            to_date="2026-06-22",
            download=True,
            key_getter=_key,
            json_getter=self._json_getter,
            file_downloader=self._downloader,
            clock=_clock,
            raw_root=self.raw,
            meta_root=self.meta,
            sleep_sec=0,
        )
        self.assertEqual(res["downloaded_count"], 1)
        self.assertEqual(res["skipped_existing_count"], 0)
        raw_path = self.raw / "equities/bars/daily/premium/live/equities_bars_daily_20260622.csv.gz"
        self.assertTrue(raw_path.exists())
        text = Path(res["manifest_path"]).read_text(encoding="utf-8")
        self.assertNotIn(SECRET, text)
        self.assertNotIn("download.example", text)
        manifest = json.loads(text)
        self.assertEqual(manifest["from"], "2026-06-22")
        self.assertEqual(manifest["to"], "2026-06-22")
        self.assertEqual(manifest["downloaded_files"][0]["status"], "downloaded")
        self.assertEqual(manifest["downloaded_files"][0]["raw_hash_uncompressed"],
                         jquants_bulk._hash_gzip_payload(raw_path))

    def test_skip_existing_with_matching_size(self):
        raw_path = self.raw / "equities/bars/daily/premium/live/equities_bars_daily_20260622.csv.gz"
        raw_path.parent.mkdir(parents=True)
        raw_path.write_bytes(_gz_bytes())
        called = {"download": 0}

        def downloader(url, dest, *, timeout):
            called["download"] += 1

        res = jquants_bulk.fetch_bulk(
            CFG,
            endpoints=["/equities/bars/daily"],
            from_date="2026-06-22",
            to_date="2026-06-22",
            download=True,
            key_getter=_key,
            json_getter=self._json_getter,
            file_downloader=downloader,
            clock=_clock,
            raw_root=self.raw,
            meta_root=self.meta,
            sleep_sec=0,
        )
        self.assertEqual(called["download"], 0)
        self.assertEqual(res["skipped_existing_count"], 1)

    def test_errors_are_redacted_and_do_not_write_raw(self):
        def bad_json_getter(url, headers, *, timeout, max_bytes):
            raise RuntimeError("boom " + SECRET)

        res = jquants_bulk.fetch_bulk(
            CFG,
            endpoints=["/equities/bars/daily"],
            from_date="2026-06-22",
            to_date="2026-06-22",
            download=True,
            key_getter=_key,
            json_getter=bad_json_getter,
            clock=_clock,
            raw_root=self.raw,
            meta_root=self.meta,
            sleep_sec=0,
        )
        self.assertEqual(res["total_files"], 0)
        self.assertEqual(len(res["errors"]), 1)
        self.assertNotIn(SECRET, str(res))
        self.assertFalse(self.raw.exists())

    def test_unsafe_endpoint_and_key_path_are_rejected(self):
        with self.assertRaises(SystemExit):
            jquants_bulk.fetch_bulk(CFG, endpoints=["/../bad"], key_getter=_key,
                                    json_getter=self._json_getter, raw_root=self.raw,
                                    meta_root=self.meta, sleep_sec=0)
        with self.assertRaises(RuntimeError):
            jquants_bulk._safe_key_path("../escape.csv.gz", raw_root=self.raw)

    def test_date_filter_rejects_endpoint_mix(self):
        with self.assertRaises(SystemExit):
            jquants_bulk.fetch_bulk(CFG, endpoints=["/equities/bars/daily"], date_filter="2026-06-22",
                                    key_getter=_key, json_getter=self._json_getter,
                                    raw_root=self.raw, meta_root=self.meta, sleep_sec=0)

    def test_cli_help_ok(self):
        p = subprocess.run([sys.executable, "-m", "radar", "fetch-jquants-bulk", "--help"],
                           cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("J-Quants Premium Bulk", p.stdout)


if __name__ == "__main__":
    unittest.main()
