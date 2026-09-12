#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 -m json.tool manifest.json >/dev/null
python3 -m json.tool contracts/actions-v1.json >/dev/null
python3 -m py_compile bin/obsws.py bin/obsbrowser.py bin/audioctl.py bin/safetyctl.py bin/collabctl.py tests/test_obsws.py tests/test_obsbrowser.py tests/test_audioctl.py tests/test_safetyctl.py tests/test_collabctl.py
bash -n bin/streamerctl

python3 - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text())
assert manifest["schemaVersion"] == 1
assert manifest["id"] == "io.github.drecullith.streamer"
assert {"service", "bar-widget"}.issubset(set(manifest["kinds"]))
assert manifest["entryPoints"]["service"] == "Service.qml"
assert manifest["entryPoints"]["barWidget"] == "BarWidget.qml"

contract = json.loads(Path("contracts/actions-v1.json").read_text())
actions = {entry["id"]: entry for entry in contract["actions"]}
required = (
    "mode.enable", "mode.disable", "privacy.enable", "privacy.disable",
    "obs.launch", "stream.start", "stream.stop", "record.start", "record.stop",
    "replay.start", "replay.stop", "clip.save", "scene.set",
    "mic.select", "mic.next", "mic.mute", "mic.unmute", "mic.toggle", "mic.volume",
    "workspace.enter", "workspace.exit", "window.check", "safety.refresh",
    "emergency.end-live", "emergency.stop-all",
    "collab.create", "collab.rotate", "collab.reset", "collab.open-director",
    "collab.copy-invite", "collab.copy-program", "collab.slot-rotate",
    "collab.copy-slot-invite", "collab.copy-slot-source",
    "collab.obs-add-program", "collab.obs-add-slot",
)
for name in required:
    assert name in actions, name
    assert actions[name]["implemented"] is True, name

for high_impact in (
    "obs.launch", "stream.start", "stream.stop", "record.start", "record.stop",
    "replay.start", "replay.stop", "scene.set", "workspace.enter",
    "emergency.end-live", "emergency.stop-all", "collab.rotate", "collab.reset",
    "collab.open-director", "collab.copy-invite", "collab.copy-program",
    "collab.slot-rotate", "collab.copy-slot-invite", "collab.copy-slot-source",
    "collab.obs-add-program", "collab.obs-add-slot",
):
    assert actions[high_impact]["agentConfirmation"] == "required", high_impact
PY

# Controllers must be safe to query on a generic CI machine.
bash bin/streamerctl status | python3 -m json.tool >/dev/null
python3 bin/obsws.py status | python3 -m json.tool >/dev/null
python3 bin/audioctl.py status | python3 -m json.tool >/dev/null
python3 bin/safetyctl.py status | python3 -m json.tool >/dev/null
python3 bin/collabctl.py status | python3 -m json.tool >/dev/null

python3 -m unittest -v tests/test_obsws.py tests/test_obsbrowser.py tests/test_audioctl.py tests/test_safetyctl.py tests/test_collabctl.py

# Future-integration architecture stays generic in the public project docs.
if grep -Rin --exclude='*.pyc' --exclude-dir='__pycache__' 'lychnos' README.md docs contracts; then
  echo "public docs contain a private future-integration name" >&2
  exit 1
fi

# Secret-bearing collaboration fields must never be part of generic status.
if python3 bin/collabctl.py status | grep -E '"(room|password|streamId|controlId|inviteUrl|programUrl|directorUrl)"'; then
  echo "collaboration status exposes credentials" >&2
  exit 1
fi

echo "smoke tests passed"
