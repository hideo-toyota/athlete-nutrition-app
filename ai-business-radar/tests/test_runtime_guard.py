"""Tests for canonical checkout guardrails."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from radar.runtime_guard import ALLOW_NON_CANONICAL_ENV, canonical_status, enforce_canonical_root


class RuntimeGuardTests(unittest.TestCase):
    def test_canonical_status_detects_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            cfg = {"runtime": {"canonical_root": str(root)}}
            status = canonical_status(root, cfg)
        self.assertTrue(status["configured"])
        self.assertTrue(status["is_canonical"])

    def test_analysis_command_stops_outside_canonical(self):
        with tempfile.TemporaryDirectory() as current, tempfile.TemporaryDirectory() as canonical:
            cfg = {"runtime": {"canonical_root": canonical}}
            with self.assertRaises(SystemExit) as cm:
                enforce_canonical_root(Path(current), cfg, "investor-brief")
        msg = str(cm.exception)
        self.assertIn("canonical root mismatch", msg)
        self.assertIn("current:", msg)
        self.assertIn("expected:", msg)

    def test_diagnostic_command_is_not_blocked(self):
        with tempfile.TemporaryDirectory() as current, tempfile.TemporaryDirectory() as canonical:
            cfg = {"runtime": {"canonical_root": canonical}}
            enforce_canonical_root(Path(current), cfg, "doctor")

    def test_dry_run_is_not_blocked(self):
        with tempfile.TemporaryDirectory() as current, tempfile.TemporaryDirectory() as canonical:
            cfg = {"runtime": {"canonical_root": canonical}}
            enforce_canonical_root(Path(current), cfg, "daily-update", dry_run=True)

    def test_explicit_env_override_is_required_for_scratch_analysis(self):
        with tempfile.TemporaryDirectory() as current, tempfile.TemporaryDirectory() as canonical:
            cfg = {"runtime": {"canonical_root": canonical}}
            with mock.patch.dict(os.environ, {ALLOW_NON_CANONICAL_ENV: "1"}):
                enforce_canonical_root(Path(current), cfg, "investor-brief")


if __name__ == "__main__":
    unittest.main()
