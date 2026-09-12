#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("onboardingctl", ROOT / "bin" / "onboardingctl.py")
assert SPEC and SPEC.loader
onboardingctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(onboardingctl)


class OnboardingCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        state_root = Path(self.tempdir.name) / "state" / "omarchy-streamer"
        onboardingctl.STATE_ROOT = state_root
        onboardingctl.STATE_FILE = state_root / "onboarding.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_initial_status_is_incomplete(self) -> None:
        state = onboardingctl.status()
        self.assertTrue(state["ready"])
        self.assertFalse(state["completed"])
        self.assertEqual(state["tourVersion"], onboardingctl.TOUR_VERSION)
        self.assertIsNone(state["completedAt"])

    def test_complete_persists_secure_state(self) -> None:
        result = onboardingctl.complete()
        self.assertTrue(result["ok"])
        state = onboardingctl.status()
        self.assertTrue(state["completed"])
        self.assertIsInstance(state["completedAt"], int)
        self.assertEqual(stat.S_IMODE(onboardingctl.STATE_FILE.stat().st_mode), 0o600)

    def test_reset_makes_tour_first_run_again(self) -> None:
        onboardingctl.complete()
        onboardingctl.reset()
        self.assertFalse(onboardingctl.status()["completed"])
        self.assertFalse(onboardingctl.STATE_FILE.exists())

    def test_old_tour_version_is_not_current_completion(self) -> None:
        onboardingctl.ensure_state_dir()
        onboardingctl.STATE_FILE.write_text('{"version":0,"completedAt":1}\n', encoding="utf-8")
        self.assertFalse(onboardingctl.status()["completed"])


if __name__ == "__main__":
    unittest.main()
