#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("profilectl", ROOT / "bin" / "profilectl.py")
assert SPEC and SPEC.loader
profilectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profilectl)


class ProfileCtlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name) / "state" / "omarchy-streamer"
        profilectl.STATE_ROOT = root
        profilectl.PROFILE_FILE = root / "profile.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_profile(self):
        status = profilectl.status()
        self.assertEqual(status["active"], "gaming")
        self.assertEqual(status["guestRefreshSeconds"], 30)

    def test_apply_and_secure_permissions(self):
        result = profilectl.perform("profile.apply", "podcast")
        self.assertEqual(result["profile"], "podcast")
        self.assertEqual(profilectl.status()["guestLayout"], "grid")
        self.assertEqual(stat.S_IMODE(profilectl.PROFILE_FILE.stat().st_mode), 0o600)

    def test_next_previous_wrap(self):
        profilectl.perform("profile.apply", "low-spec")
        self.assertEqual(profilectl.perform("profile.next")["profile"], "gaming")
        self.assertEqual(profilectl.perform("profile.previous")["profile"], "low-spec")

    def test_unknown_profile_fails(self):
        with self.assertRaises(profilectl.ProfileError):
            profilectl.perform("profile.apply", "spaceship")


if __name__ == "__main__":
    unittest.main()
