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
AUDIOCTL = ROOT / "bin" / "audioctl.py"


class AudioCtlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "wpctl.log"
        fake = self.bin / "wpctl"
        fake.write_text(
            """#!/usr/bin/env bash
set -eu
printf '%s\\n' \"$*\" >> \"$FAKE_WPCTL_LOG\"
case \"${1:-} ${2:-} ${3:-}\" in
  'list audio sources')
    printf '41\\talsa_input.usb-Mic_A\\tAudio/Source\\t*\\n'
    printf '42\\talsa_input.usb-Mic_B\\tAudio/Source\\t\\n'
    ;;
  'get-volume 41 ')
    printf 'Volume: 0.75\\n'
    ;;
  'get-volume 42 ')
    printf 'Volume: 0.55 [MUTED]\\n'
    ;;
  'set-mute 41 '*|'set-mute 42 '*|'set-volume 41 '*|'set-volume 42 '*)
    ;;
  *)
    printf 'unexpected wpctl call: %s\\n' \"$*\" >&2
    exit 3
    ;;
esac
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env.get("PATH", "")
        self.env["XDG_STATE_HOME"] = str(self.root / "state")
        self.env["FAKE_WPCTL_LOG"] = str(self.log)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def call(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(AUDIOCTL), *args],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def status(self) -> dict:
        proc = self.call("status")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_default_source_then_cycle_and_control(self) -> None:
        initial = self.status()
        self.assertTrue(initial["ready"])
        self.assertEqual(initial["selectedSourceName"], "alsa_input.usb-Mic_A")
        self.assertEqual(initial["volumePercent"], 75)
        self.assertFalse(initial["muted"])
        self.assertEqual(len(initial["sources"]), 2)

        switched = self.call("action", "mic.next")
        self.assertEqual(switched.returncode, 0, switched.stderr)
        self.assertEqual(json.loads(switched.stdout)["selectedSourceName"], "alsa_input.usb-Mic_B")

        after = self.status()
        self.assertEqual(after["selectedSourceName"], "alsa_input.usb-Mic_B")
        self.assertEqual(after["volumePercent"], 55)
        self.assertTrue(after["muted"])

        self.assertEqual(self.call("action", "mic.unmute").returncode, 0)
        self.assertEqual(self.call("action", "mic.volume", "95").returncode, 0)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("set-mute 42 0", log)
        self.assertIn("set-volume 42 95%", log)

    def test_missing_saved_source_is_reported_not_replaced(self) -> None:
        state_dir = Path(self.env["XDG_STATE_HOME"]) / "omarchy-streamer"
        state_dir.mkdir(parents=True)
        (state_dir / "audio.json").write_text(
            '{"selectedSourceName":"alsa_input.usb-Unplugged_Mic"}\n',
            encoding="utf-8",
        )
        state = self.status()
        self.assertFalse(state["selectedPresent"])
        self.assertEqual(state["selectedSourceName"], "alsa_input.usb-Unplugged_Mic")
        self.assertIn("unavailable", state["error"])

        mute = self.call("action", "mic.mute")
        self.assertNotEqual(mute.returncode, 0)
        self.assertIn("unavailable", mute.stderr)


if __name__ == "__main__":
    unittest.main()
