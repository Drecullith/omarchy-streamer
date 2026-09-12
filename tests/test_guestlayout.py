#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("guestlayout", ROOT / "bin" / "guestlayout.py")
assert SPEC and SPEC.loader
guestlayout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guestlayout)


class FakeClient:
    calls = []
    items = [
        {"sourceName": "Omarchy Streamer - Guest 1", "sceneItemId": 11},
        {"sourceName": "Omarchy Streamer - Guest 2", "sceneItemId": 12},
        {"sourceName": "Omarchy Streamer - Guest 3", "sceneItemId": 13},
        {"sourceName": "Logo", "sceneItemId": 99},
    ]

    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return None

    def request(self, name, data=None):
        data = data or {}
        FakeClient.calls.append((name, data))
        if name == "GetSceneItemList":
            return {"sceneItems": list(FakeClient.items)}
        if name == "GetVideoSettings":
            return {"baseWidth": 1920, "baseHeight": 1080}
        if name in ("SetSceneItemEnabled", "SetSceneItemTransform"):
            return {}
        raise AssertionError(name)


class GuestLayoutTests(unittest.TestCase):
    def setUp(self):
        FakeClient.calls = []
        self.fake_module = type("FakeObs", (), {"ObsClient": FakeClient})

    def test_grid_uses_only_managed_guest_sources(self):
        with mock.patch.object(guestlayout, "load_obsws", return_value=self.fake_module):
            result = guestlayout.apply_layout("grid")
        self.assertEqual(result["managedGuests"], [1, 2, 3])
        transforms = [data for name, data in FakeClient.calls if name == "SetSceneItemTransform"]
        self.assertEqual(len(transforms), 3)
        self.assertTrue(all(t["sceneItemTransform"]["boundsType"] == "OBS_BOUNDS_SCALE_INNER" for t in transforms))
        self.assertNotIn(99, [t["sceneItemId"] for t in transforms])

    def test_focus_disables_other_managed_guests(self):
        with mock.patch.object(guestlayout, "load_obsws", return_value=self.fake_module):
            result = guestlayout.apply_layout("focus:2")
        self.assertEqual(result["visibleGuests"], [1, 2, 3])
        enables = {data["sceneItemId"]: data["sceneItemEnabled"] for name, data in FakeClient.calls if name == "SetSceneItemEnabled"}
        self.assertTrue(enables[11])
        self.assertTrue(enables[12])
        self.assertTrue(enables[13])
        transforms = [data for name, data in FakeClient.calls if name == "SetSceneItemTransform"]
        focus = next(t for t in transforms if t["sceneItemId"] == 12)
        self.assertEqual(focus["sceneItemTransform"]["boundsWidth"], 1440.0)

    def test_single_disables_nonselected_managed_guests(self):
        with mock.patch.object(guestlayout, "load_obsws", return_value=self.fake_module):
            result = guestlayout.apply_layout("single")
        self.assertEqual(result["visibleGuests"], [1])
        enables = {data["sceneItemId"]: data["sceneItemEnabled"] for name, data in FakeClient.calls if name == "SetSceneItemEnabled"}
        self.assertEqual(enables, {11: True, 12: False, 13: False})

    def test_bad_focus_slot_fails(self):
        with mock.patch.object(guestlayout, "load_obsws", return_value=self.fake_module):
            with self.assertRaises(guestlayout.LayoutError):
                guestlayout.apply_layout("focus:4")


if __name__ == "__main__":
    unittest.main()
