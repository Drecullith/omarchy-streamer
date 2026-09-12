#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("obsbrowser", ROOT / "bin" / "obsbrowser.py")
assert SPEC and SPEC.loader
obsbrowser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(obsbrowser)


class FakeClient:
    calls = []
    scenes = ["Gameplay"]
    inputs = []
    items = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def request(self, name, data=None):
        data = data or {}
        FakeClient.calls.append((name, data))
        if name == "GetSceneList":
            return {"scenes": [{"sceneName": s} for s in FakeClient.scenes]}
        if name == "CreateScene":
            FakeClient.scenes.append(data["sceneName"])
            return {}
        if name == "GetInputList":
            return {"inputs": list(FakeClient.inputs)}
        if name == "CreateInput":
            FakeClient.inputs.append({"inputName": data["inputName"], "inputKind": data["inputKind"]})
            FakeClient.items.setdefault(data["sceneName"], []).append(data["inputName"])
            return {"sceneItemId": 1}
        if name == "SetInputSettings":
            return {}
        if name == "GetSceneItemList":
            return {"sceneItems": [{"sourceName": n} for n in FakeClient.items.get(data["sceneName"], [])]}
        if name == "CreateSceneItem":
            FakeClient.items.setdefault(data["sceneName"], []).append(data["sourceName"])
            return {"sceneItemId": 2}
        raise AssertionError(name)


class ObsBrowserTests(unittest.TestCase):
    def setUp(self):
        FakeClient.calls = []
        FakeClient.scenes = ["Gameplay"]
        FakeClient.inputs = []
        FakeClient.items = {}
        self.fake_module = type("FakeObs", (), {"ObsClient": FakeClient})

    def test_creates_scene_and_browser_source(self):
        with mock.patch.object(obsbrowser, "load_obsws", return_value=self.fake_module):
            result = obsbrowser.ensure_browser_source(
                "https://vdo.ninja/?scene=0&room=x",
                scene_name="Omarchy Guests",
                input_name="Omarchy Streamer - Guests",
            )
        self.assertTrue(result["createdScene"])
        self.assertTrue(result["createdInput"])
        create_input = next(data for name, data in FakeClient.calls if name == "CreateInput")
        self.assertEqual(create_input["inputKind"], "browser_source")
        self.assertEqual(create_input["inputSettings"]["width"], 1920)
        self.assertIn("vdo.ninja", create_input["inputSettings"]["url"])

    def test_updates_existing_source_and_adds_to_scene(self):
        FakeClient.scenes = ["Omarchy Guests"]
        FakeClient.inputs = [{"inputName": "Omarchy Streamer - Guests", "inputKind": "browser_source"}]
        with mock.patch.object(obsbrowser, "load_obsws", return_value=self.fake_module):
            result = obsbrowser.ensure_browser_source(
                "https://vdo.ninja/?scene=0&room=y",
                scene_name="Omarchy Guests",
                input_name="Omarchy Streamer - Guests",
            )
        self.assertFalse(result["createdInput"])
        self.assertTrue(result["addedToScene"])
        self.assertTrue(any(name == "SetInputSettings" for name, _ in FakeClient.calls))
        self.assertTrue(any(name == "CreateSceneItem" for name, _ in FakeClient.calls))

    def test_refuses_name_collision_with_non_browser_input(self):
        FakeClient.scenes = ["Omarchy Guests"]
        FakeClient.inputs = [{"inputName": "Omarchy Streamer - Guests", "inputKind": "image_source"}]
        with mock.patch.object(obsbrowser, "load_obsws", return_value=self.fake_module):
            with self.assertRaises(obsbrowser.BrowserSourceError):
                obsbrowser.ensure_browser_source(
                    "https://vdo.ninja/?scene=0&room=z",
                    scene_name="Omarchy Guests",
                    input_name="Omarchy Streamer - Guests",
                )


if __name__ == "__main__":
    unittest.main()
