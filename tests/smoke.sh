#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python -m json.tool manifest.json >/dev/null
python -m json.tool contracts/actions-v1.json >/dev/null
bash -n bin/streamerctl

python - <<'PY'
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
):
    assert required in actions, required

for high_impact in ("obs.launch", "stream.start", "stream.stop", "record.start", "record.stop", "scene.set"):
    assert actions[high_impact]["agentConfirmation"] == "required", high_impact
PY

# The controller must be safe to query on a generic CI machine where OBS,
# PipeWire, and omarchy-shell probably do not exist.
bash bin/streamerctl status | python -m json.tool >/dev/null

echo "smoke tests passed"
