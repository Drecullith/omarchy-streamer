#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
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

    def test_create_is_secure_and_status_does_not_expose_any_credentials(self) -> None:
        session = collabctl.create_session()
        self.assertEqual(len(session["slots"]), 4)
        self.assertEqual(stat.S_IMODE(collabctl.SESSION_FILE.stat().st_mode), 0o600)
        snapshot = collabctl.status()
        serialized = json.dumps(snapshot)
        self.assertEqual(snapshot["slotCount"], 4)
        self.assertFalse(snapshot["credentialsExposed"])
        self.assertNotIn(session["room"], serialized)
        self.assertNotIn(session["password"], serialized)
        for slot in session["slots"]:
            self.assertNotIn(slot["streamId"], serialized)
            self.assertNotIn(slot["controlId"], serialized)

    def test_slot_invite_has_stable_stream_identity_and_private_control_id(self) -> None:
        session = collabctl.create_session()
        slot = collabctl.get_slot(session, 1)
        guest = collabctl.slot_url(session, slot, "guest")
        solo = collabctl.slot_url(session, slot, "solo")
        self.assertIn("push=", guest)
        self.assertIn("api=", guest)
        self.assertIn("label=Guest+1", guest)
        self.assertIn("view=", solo)
        self.assertIn("scene=0", solo)
        self.assertIn("cleanoutput", solo)
        self.assertNotIn(slot["controlId"], solo)

    def test_rotate_one_slot_does_not_rotate_room_or_other_slots(self) -> None:
        before = collabctl.create_session()
        room = before["room"]
        second_stream = before["slots"][1]["streamId"]
        first_stream = before["slots"][0]["streamId"]
        collabctl.rotate_slot("1")
        after = collabctl.require_session()
        self.assertEqual(room, after["room"])
        self.assertNotEqual(first_stream, after["slots"][0]["streamId"])
        self.assertEqual(second_stream, after["slots"][1]["streamId"])

    def test_copy_slot_invite_does_not_return_secret_url(self) -> None:
        collabctl.create_session()
        with mock.patch.object(collabctl.shutil, "which", return_value="/usr/bin/wl-copy"), \
             mock.patch.object(collabctl.subprocess, "run") as run:
            result = collabctl.perform("collab.copy-slot-invite", "2")
        self.assertEqual(result["slot"], 2)
        self.assertNotIn("url", result)
        copied = run.call_args.kwargs["input"]
        self.assertIn("push=", copied)
        self.assertIn("api=", copied)

    def test_obs_add_slot_passes_secret_only_in_process_memory(self) -> None:
        collabctl.create_session()
        calls = []
        fake = type("FakeAdapter", (), {
            "ensure_browser_source": staticmethod(lambda url, **kw: calls.append((url, kw)) or {
                "ok": True, "sceneName": kw["scene_name"], "inputName": kw["input_name"],
                "createdScene": True, "createdInput": True, "addedToScene": True,
            })
        })
        with mock.patch.object(collabctl, "load_obsbrowser", return_value=fake):
            result = collabctl.perform("collab.obs-add-slot", "3")
        self.assertEqual(result["slot"], 3)
        self.assertEqual(result["inputName"], "Omarchy Streamer - Guest 3")
        self.assertIn("view=", calls[0][0])
        serialized = json.dumps(result)
        session = collabctl.require_session()
        self.assertNotIn(session["password"], serialized)
        self.assertNotIn(session["slots"][2]["streamId"], serialized)

    def test_old_v05_room_migrates_without_changing_room_secret(self) -> None:
        collabctl.ensure_state_dir()
        old = {"version": 1, "provider": "vdo.ninja", "room": "legacy_room", "password": "legacy_secret", "createdAt": 1}
        collabctl.SESSION_FILE.write_text(json.dumps(old), encoding="utf-8")
        loaded = collabctl.load_session()
        self.assertEqual(loaded["room"], "legacy_room")
        self.assertEqual(loaded["password"], "legacy_secret")
        self.assertEqual(len(loaded["slots"]), 4)


if __name__ == "__main__":
    unittest.main()
