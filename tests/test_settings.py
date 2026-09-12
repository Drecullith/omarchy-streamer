#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("streamer_settings", ROOT / "bin" / "settings.py")
assert SPEC and SPEC.loader
settings = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(settings)


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name) / "config" / "omarchy-streamer"
        settings.CONFIG_ROOT = root
        settings.SETTINGS_FILE = root / "settings.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_defaults_and_secure_write(self) -> None:
        state = settings.resolved()
        self.assertEqual(state["values"]["safeWorkspace"], "stream-safe")
        result = settings.set_value("guestSceneName", "Guests & Friends")
        self.assertTrue(result["ok"])
        self.assertEqual(stat.S_IMODE(settings.SETTINGS_FILE.stat().st_mode), 0o600)
        raw = json.loads(settings.SETTINGS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["guestSceneName"], "Guests & Friends")

    def test_environment_override_wins_without_rewriting_file(self) -> None:
        settings.set_value("safeWorkspace", "stream-room")
        with mock.patch.dict(os.environ, {"OMARCHY_STREAMER_SAFE_WORKSPACE": "broadcast"}, clear=False):
            state = settings.resolved()
        self.assertEqual(state["values"]["safeWorkspace"], "broadcast")
        self.assertEqual(state["sources"]["safeWorkspace"], "environment")
        raw = json.loads(settings.SETTINGS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(raw["safeWorkspace"], "stream-room")

    def test_rejects_unknown_and_unsafe_values(self) -> None:
        with self.assertRaises(settings.SettingsError):
            settings.set_value("mystery", "1")
        with self.assertRaises(settings.SettingsError):
            settings.set_value("safeWorkspace", "bad workspace name")
        with self.assertRaises(settings.SettingsError):
            settings.set_value("guestStateMaxAge", "2")
        with self.assertRaises(settings.SettingsError):
            settings.set_value("guestControlTimeout", "99")

    def test_reset_one_or_all(self) -> None:
        settings.set_value("safeWorkspace", "broadcast")
        settings.set_value("guestStateMaxAge", "45")
        settings.reset_value("safeWorkspace")
        state = settings.resolved()
        self.assertEqual(state["values"]["safeWorkspace"], "stream-safe")
        self.assertEqual(state["values"]["guestStateMaxAge"], 45)
        settings.reset_value()
        self.assertFalse(settings.SETTINGS_FILE.exists())

    def test_invalid_file_fails_closed_in_resolved_but_status_is_safe(self) -> None:
        settings.ensure_config_dir()
        settings.SETTINGS_FILE.write_text('{"schemaVersion":1,"unknown":true}\n', encoding="utf-8")
        with self.assertRaises(settings.SettingsError):
            settings.resolved()
        safe = settings.status()
        self.assertFalse(safe["ready"])
        self.assertIn("unknown setting", safe["error"])
        self.assertEqual(safe["values"]["safeWorkspace"], "stream-safe")


if __name__ == "__main__":
    unittest.main()
