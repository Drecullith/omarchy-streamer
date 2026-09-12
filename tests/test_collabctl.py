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
SPEC = importlib.util.spec_from_file_location("collabctl", ROOT / "bin" / "collabctl.py")
assert SPEC and SPEC.loader
collabctl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collabctl)


class CollabCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name) / "state" / "omarchy-streamer"
        collabctl.STATE_ROOT = root
        collabctl.SESSION_FILE = root / "collab-session.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_is_secure_and_status_does_not_expose_credentials(self) -> None:
        session = collabctl.create_session()
        self.assertEqual(session["provider"], "vdo.ninja")
        self.assertTrue(session["room"].startswith("omarchy-"))
        self.assertGreaterEqual(len(session["password"]), 24)

        mode = stat.S_IMODE(collabctl.SESSION_FILE.stat().st_mode)
        self.assertEqual(mode, 0o600)

        snapshot = collabctl.status()
        serialized = json.dumps(snapshot)
        self.assertTrue(snapshot["active"])
        self.assertFalse(snapshot["credentialsExposed"])
        self.assertNotIn(session["room"], serialized)
        self.assertNotIn(session["password"], serialized)

    def test_create_is_idempotent_and_rotate_changes_secret(self) -> None:
        first = collabctl.create_session()
        again = collabctl.create_session()
        self.assertEqual(first["room"], again["room"])
        self.assertEqual(first["password"], again["password"])

        rotated = collabctl.create_session(force=True)
        self.assertNotEqual(first["room"], rotated["room"])
        self.assertNotEqual(first["password"], rotated["password"])

    def test_urls_are_password_protected_and_program_is_clean_scene_zero(self) -> None:
        session = collabctl.create_session()
        director = collabctl.provider_url(session, "director")
        guest = collabctl.provider_url(session, "guest")
        program = collabctl.provider_url(session, "program")

        self.assertIn("director=", director)
        self.assertIn("password=", director)
        self.assertIn("room=", guest)
        self.assertIn("password=", guest)
        self.assertIn("autostart", guest)
        self.assertIn("scene=0", program)
        self.assertIn("cleanoutput", program)
        self.assertIn("password=", program)

    def test_copy_invite_uses_wayland_clipboard_without_returning_url(self) -> None:
        collabctl.create_session()
        with mock.patch.object(collabctl.shutil, "which", side_effect=lambda name: "/usr/bin/wl-copy" if name == "wl-copy" else None), \
             mock.patch.object(collabctl.subprocess, "run") as run:
            result = collabctl.perform("collab.copy-invite")
        self.assertTrue(result["ok"])
        self.assertNotIn("url", result)
        self.assertEqual(run.call_args.args[0], ["/usr/bin/wl-copy"])
        copied = run.call_args.kwargs["input"]
        self.assertTrue(copied.startswith("https://vdo.ninja/?"))
        self.assertIn("password=", copied)

    def test_open_director_uses_xdg_open(self) -> None:
        collabctl.create_session()
        with mock.patch.object(collabctl.shutil, "which", side_effect=lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None), \
             mock.patch.object(collabctl.subprocess, "Popen") as popen:
            result = collabctl.perform("collab.open-director")
        self.assertTrue(result["ok"])
        command = popen.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/xdg-open")
        self.assertIn("director=", command[1])
        self.assertIn("password=", command[1])

    def test_reset_removes_session(self) -> None:
        collabctl.create_session()
        collabctl.perform("collab.reset")
        self.assertFalse(collabctl.status()["active"])


if __name__ == "__main__":
    unittest.main()
