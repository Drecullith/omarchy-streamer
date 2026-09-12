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


class FakeVdoTimeout(RuntimeError):
    pass


class FakeVdoError(RuntimeError):
    pass


class FakeVdoApi:
    VdoApiTimeout = FakeVdoTimeout
    VdoApiError = FakeVdoError
    mic_calls: list[tuple[str, bool]] = []
    hangups: list[str] = []

    @staticmethod
    def probe(control_id: str) -> bool:
        return True

    @classmethod
    def set_mic(cls, control_id: str, enabled: bool) -> bool:
        cls.mic_calls.append((control_id, enabled))
        return enabled

    @classmethod
    def hangup(cls, control_id: str) -> None:
        cls.hangups.append(control_id)


class CollabCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name) / "state" / "omarchy-streamer"
        collabctl.STATE_ROOT = root
        collabctl.SESSION_FILE = root / "collab-session.json"
        collabctl.GUEST_STATE_FILE = root / "collab-guest-state.json"
        FakeVdoApi.mic_calls = []
        FakeVdoApi.hangups = []

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_create_is_secure_and_status_does_not_expose_any_credentials(self) -> None:
        session = collabctl.create_session()
        self.assertEqual(len(session["slots"]), 4)
        self.assertEqual(stat.S_IMODE(collabctl.SESSION_FILE.stat().st_mode), 0o600)
        snapshot = collabctl.status()
        serialized = json.dumps(snapshot)
        self.assertEqual(snapshot["slotCount"], 4)
        self.assertEqual(len(snapshot["guests"]), 4)
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
        collabctl.update_guest_state(1, online=True)
        collabctl.rotate_slot("1")
        after = collabctl.require_session()
        self.assertEqual(room, after["room"])
        self.assertNotEqual(first_stream, after["slots"][0]["streamId"])
        self.assertEqual(second_stream, after["slots"][1]["streamId"])
        self.assertIsNone(collabctl.safe_guest_states(after)[0]["online"])

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

    def test_parallel_guest_refresh_keeps_all_four_slots_and_no_secrets(self) -> None:
        session = collabctl.create_session()
        with mock.patch.object(collabctl, "load_vdoapi", return_value=FakeVdoApi):
            result = collabctl.perform("collab.guest-refresh")
        self.assertEqual(len(result["guests"]), 4)
        self.assertTrue(all(guest["online"] is True for guest in result["guests"]))
        self.assertEqual(stat.S_IMODE(collabctl.GUEST_STATE_FILE.stat().st_mode), 0o600)
        serialized = json.dumps(collabctl.status())
        for slot in session["slots"]:
            self.assertNotIn(slot["controlId"], serialized)
            self.assertNotIn(slot["streamId"], serialized)

    def test_remote_mic_state_comes_from_callback_and_is_cached(self) -> None:
        session = collabctl.create_session()
        first = session["slots"][0]
        with mock.patch.object(collabctl, "load_vdoapi", return_value=FakeVdoApi):
            muted = collabctl.perform("collab.guest-mute", "1")
            unmuted = collabctl.perform("collab.guest-unmute", "1")
        self.assertFalse(muted["micEnabled"])
        self.assertTrue(unmuted["micEnabled"])
        self.assertEqual(FakeVdoApi.mic_calls, [(first["controlId"], False), (first["controlId"], True)])
        state = collabctl.status()["guests"][0]
        self.assertTrue(state["online"])
        self.assertTrue(state["micEnabled"])

    def test_disconnect_marks_guest_offline_after_callback(self) -> None:
        session = collabctl.create_session()
        first = session["slots"][0]
        with mock.patch.object(collabctl, "load_vdoapi", return_value=FakeVdoApi):
            result = collabctl.perform("collab.guest-disconnect", "1")
        self.assertFalse(result["online"])
        self.assertEqual(FakeVdoApi.hangups, [first["controlId"]])
        self.assertFalse(collabctl.status()["guests"][0]["online"])

    def test_probe_timeout_is_offline_not_online(self) -> None:
        class TimeoutApi(FakeVdoApi):
            @staticmethod
            def probe(control_id: str) -> bool:
                raise FakeVdoTimeout("timeout")
        collabctl.create_session()
        with mock.patch.object(collabctl, "load_vdoapi", return_value=TimeoutApi):
            result = collabctl.perform("collab.guest-refresh")
        self.assertTrue(all(guest["online"] is False for guest in result["guests"]))
        self.assertTrue(all(guest["error"] == "timeout" for guest in result["guests"]))


if __name__ == "__main__":
    unittest.main()
