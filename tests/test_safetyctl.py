#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAFETYCTL = ROOT / "bin" / "safetyctl.py"


class SafetyCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.bin = root / "bin"
        self.bin.mkdir()
        self.state = root / "hypr-state.json"
        self.xdg_state = root / "state"
        self.xdg_config = root / "config"
        (self.xdg_config / "omarchy-streamer").mkdir(parents=True)
        (self.xdg_config / "omarchy-streamer" / "sensitive-apps.txt").write_text(
            "class:secret-app\n", encoding="utf-8"
        )
        self.state.write_text(
            json.dumps(
                {
                    "workspace": "2",
                    "window": {
                        "class": "Secret-App",
                        "title": "do-not-print-this-secret-title",
                    },
                }
            ),
            encoding="utf-8",
        )

        fake = self.bin / "hyprctl"
        fake.write_text(
            """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p=Path(os.environ["FAKE_HYPR_STATE"])
s=json.loads(p.read_text())
a=sys.argv[1:]
if a == ["activeworkspace", "-j"]:
    print(json.dumps({"name": s["workspace"]}))
elif a == ["activewindow", "-j"]:
    print(json.dumps(s["window"]))
elif len(a) == 3 and a[:2] == ["dispatch", "workspace"]:
    target=a[2]
    s["workspace"]=target[5:] if target.startswith("name:") else target
    p.write_text(json.dumps(s))
    print("ok")
else:
    print("unsupported", file=sys.stderr)
    sys.exit(2)
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)

        self.env = os.environ.copy()
        self.env.update(
            PATH=f"{self.bin}:{self.env.get('PATH','')}",
            FAKE_HYPR_STATE=str(self.state),
            XDG_STATE_HOME=str(self.xdg_state),
            XDG_CONFIG_HOME=str(self.xdg_config),
            OMARCHY_STREAMER_SENSITIVE_DEFAULTS="0",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_ctl(self, *args: str) -> dict:
        cp = subprocess.run(
            [sys.executable, str(SAFETYCTL), *args],
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(cp.stdout)

    def test_sensitive_window_warns_without_exposing_title(self) -> None:
        cp = subprocess.run(
            [sys.executable, str(SAFETYCTL), "status"],
            env=self.env,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertNotIn("do-not-print-this-secret-title", cp.stdout)
        data = json.loads(cp.stdout)
        self.assertTrue(data["ready"])
        self.assertTrue(data["sensitiveActive"])
        self.assertEqual(data["sensitiveRule"], "class:secret-app")
        self.assertEqual(data["activeWindowClass"], "Secret-App")

    def test_workspace_enter_and_restore(self) -> None:
        entered = self.run_ctl("action", "workspace.enter")
        self.assertEqual(entered["previousWorkspace"], "2")
        self.assertEqual(json.loads(self.state.read_text())["workspace"], "stream-safe")

        status = self.run_ctl("status")
        self.assertTrue(status["streamSafeActive"])

        exited = self.run_ctl("action", "workspace.exit")
        self.assertEqual(exited["workspace"], "2")
        self.assertEqual(json.loads(self.state.read_text())["workspace"], "2")


if __name__ == "__main__":
    unittest.main()
