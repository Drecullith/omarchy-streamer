#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("diagnostics", ROOT / "bin" / "diagnostics.py")
assert SPEC and SPEC.loader
diagnostics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(diagnostics)


class DiagnosticsTests(unittest.TestCase):
    def test_snapshot_omits_identifying_and_secret_fields(self) -> None:
        status = {
            "version": 10,
            "active": True,
            "privacy": True,
            "dndState": "on",
            "pythonReady": True,
            "obsInstalled": True,
            "obsRunning": True,
            "pipewireReady": True,
            "wpctlInstalled": True,
            "obsWebSocket": {"connected": True, "streaming": False, "recording": True, "replayBuffer": True, "currentScene": "PRIVATE SCENE", "error": "OBS PASSWORD fake-secret"},
            "audio": {"ready": True, "selectedSourceName": "My Real Mic Serial 123", "selectedPresent": True, "muted": False, "volumePercent": 93},
            "safety": {"ready": True, "workspaceName": "work-private", "streamSafeActive": False, "sensitiveActive": True, "activeWindowClass": "Bitwarden", "sensitiveRule": "title:Bank"},
            "collaboration": {"ready": True, "active": True, "guestControlReady": True, "slotCount": 4, "room": "SECRETROOM", "password": "PASSWORD", "streamId": "STREAMSECRET", "controlId": "CONTROLSECRET", "guests": [
                {"slot": 1, "online": True, "stale": False, "micEnabled": True},
                {"slot": 2, "online": False, "stale": False},
                {"slot": 3, "online": True, "stale": True},
                {"slot": 4, "online": None, "stale": True},
            ]},
            "profiles": {"active": "podcast", "guestRefreshSeconds": 15},
            "onboarding": {"ready": True, "completed": True},
        }
        settings = {"ready": True, "values": {"safeWorkspace": "secret-workspace", "guestSceneName": "Secret Guest Scene", "guestStateMaxAge": 30, "guestControlTimeout": 1.4, "sensitiveDefaults": True}, "sources": {"safeWorkspace": "file", "guestSceneName": "file"}}
        snapshot = diagnostics.build_snapshot(status, settings)
        text = json.dumps(snapshot)
        for forbidden in (
            "PRIVATE SCENE", "fake-secret", "My Real Mic Serial 123", "work-private", "Bitwarden", "Bank",
            "SECRETROOM", "PASSWORD", "STREAMSECRET", "CONTROLSECRET", "secret-workspace", "Secret Guest Scene",
        ):
            self.assertNotIn(forbidden, text)
        self.assertEqual(snapshot["collaboration"]["onlineFresh"], 1)
        self.assertEqual(snapshot["collaboration"]["offline"], 1)
        self.assertEqual(snapshot["collaboration"]["stale"], 2)
        self.assertEqual(snapshot["profile"]["active"], "podcast")
        self.assertTrue(snapshot["dependencies"]["obsWebSocket"])


if __name__ == "__main__":
    unittest.main()
