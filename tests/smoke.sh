#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 -m json.tool manifest.json >/dev/null
python3 -m json.tool contracts/actions-v1.json >/dev/null
python3 -m py_compile bin/obsws.py tests/test_obsws.py
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
for required in (
    "mode.enable",
    "mode.disable",
    "privacy.enable",
    "privacy.disable",
    "obs.launch",
    "stream.start",
    "stream.stop",
    "record.start",
    "record.stop",
    "replay.start",
    "replay.stop",
    "clip.save",
    "scene.set",
):
    assert required in actions, required

for implemented in (
    "stream.start",
    "stream.stop",
    "record.start",
    "record.stop",
    "replay.start",
    "replay.stop",
    "clip.save",
    "scene.set",
):
    assert actions[implemented]["implemented"] is True, implemented

for high_impact in (
    "obs.launch",
    "stream.start",
    "stream.stop",
    "record.start",
    "record.stop",
    "replay.start",
    "replay.stop",
    "scene.set",
):
    assert actions[high_impact]["agentConfirmation"] == "required", high_impact
PY

# The controller and OBS adapter must be safe to query on a generic CI machine
# where OBS, PipeWire, and omarchy-shell probably do not exist.
bash bin/streamerctl status | python3 -m json.tool >/dev/null
python3 bin/obsws.py status | python3 -m json.tool >/dev/null

# Exercise a fake local OBS server, including a coalesced HTTP-upgrade + Hello.
python3 -m unittest -v tests/test_obsws.py

# Future-integration architecture stays generic in the public project docs.
if grep -Rin --exclude='*.pyc' --exclude-dir='__pycache__' 'lychnos' README.md docs contracts; then
  echo "public docs contain a private future-integration name" >&2
  exit 1
fi

echo "smoke tests passed"
