#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

python3 -m json.tool manifest.json >/dev/null
python3 -m json.tool contracts/actions-v1.json >/dev/null
python3 -m py_compile \
  bin/obsws.py bin/obsbrowser.py bin/audioctl.py bin/safetyctl.py bin/collabctl.py bin/vdoapi.py \
  bin/onboardingctl.py bin/profilectl.py bin/guestlayout.py bin/settings.py bin/withsettings.py bin/migrate.py bin/diagnostics.py \
  tests/test_obsws.py tests/test_obsbrowser.py tests/test_audioctl.py tests/test_safetyctl.py tests/test_collabctl.py \
  tests/test_vdoapi.py tests/test_onboardingctl.py tests/test_profilectl.py tests/test_guestlayout.py \
  tests/test_settings.py tests/test_migrate.py tests/test_diagnostics.py
bash -n bin/streamerctl

python3 - <<'PY'
import json
from pathlib import Path

manifest = json.loads(Path("manifest.json").read_text())
assert manifest["schemaVersion"] == 1
assert manifest["id"] == "io.github.drecullith.streamer"
assert {"service", "bar-widget", "overlay"}.issubset(set(manifest["kinds"]))
assert manifest["entryPoints"]["service"] == "Service.qml"
assert manifest["entryPoints"]["barWidget"] == "BarWidget.qml"
assert manifest["entryPoints"]["overlay"] == "Onboarding.qml"
assert manifest["version"] == "1.0.0"

contract = json.loads(Path("contracts/actions-v1.json").read_text())
ids = [entry["id"] for entry in contract["actions"]]
assert len(ids) == len(set(ids)), "duplicate action IDs"
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
    "collab.guest-refresh", "collab.guest-mute", "collab.guest-unmute", "collab.guest-disconnect",
    "collab.layout", "profile.apply", "profile.next", "profile.previous", "profile.layout",
    "settings.set", "settings.reset", "state.migrate", "support.snapshot", "support.copy",
    "onboarding.open", "onboarding.complete", "onboarding.reset", "health.refresh",
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
    "collab.guest-mute", "collab.guest-unmute", "collab.guest-disconnect",
    "collab.layout", "profile.layout",
):
    assert actions[high_impact]["agentConfirmation"] == "required", high_impact

assert actions["collab.guest-refresh"]["agentConfirmation"] == "none"
assert actions["support.snapshot"]["agentConfirmation"] == "none"
for name in ("profile.apply", "profile.next", "profile.previous", "settings.set", "settings.reset", "state.migrate", "support.copy"):
    assert actions[name]["agentConfirmation"] == "session", name
assert actions["onboarding.open"]["agentConfirmation"] == "none"
assert actions["onboarding.complete"]["agentConfirmation"] == "none"
assert actions["onboarding.reset"]["agentConfirmation"] == "session"
PY

# Controllers must be safe to query on a generic CI machine.
tmp_state="$(mktemp -d)"
tmp_config="$(mktemp -d)"
trap 'rm -rf "$tmp_state" "$tmp_config"' EXIT
export XDG_STATE_HOME="$tmp_state"
export XDG_CONFIG_HOME="$tmp_config"

bash bin/streamerctl status | python3 -m json.tool >/dev/null
bash bin/streamerctl support | python3 -m json.tool >/dev/null
python3 bin/obsws.py status | python3 -m json.tool >/dev/null
python3 bin/audioctl.py status | python3 -m json.tool >/dev/null
python3 bin/safetyctl.py status | python3 -m json.tool >/dev/null
python3 bin/collabctl.py status | python3 -m json.tool >/dev/null
python3 bin/onboardingctl.py status | python3 -m json.tool >/dev/null
python3 bin/profilectl.py status | python3 -m json.tool >/dev/null
python3 bin/settings.py status | python3 -m json.tool >/dev/null
python3 bin/migrate.py | python3 -m json.tool >/dev/null
bash bin/streamerctl action settings.set 'safeWorkspace=ci-safe' | python3 -m json.tool >/dev/null
python3 bin/settings.py status | grep -q 'ci-safe'
bash bin/streamerctl action settings.reset 'safeWorkspace' | python3 -m json.tool >/dev/null

python3 -m unittest -v \
  tests/test_obsws.py tests/test_obsbrowser.py tests/test_audioctl.py tests/test_safetyctl.py tests/test_collabctl.py \
  tests/test_vdoapi.py tests/test_onboardingctl.py tests/test_profilectl.py tests/test_guestlayout.py \
  tests/test_settings.py tests/test_migrate.py tests/test_diagnostics.py

# Future-integration architecture stays generic in the public project docs.
if grep -Rin --exclude='*.pyc' --exclude-dir='__pycache__' 'lychnos' README.md docs contracts; then
  echo "public docs contain a private future-integration name" >&2
  exit 1
fi

# Secret-bearing collaboration fields must never be part of generic collaboration status.
if python3 bin/collabctl.py status | grep -E '"(room|password|streamId|controlId|inviteUrl|programUrl|directorUrl)"'; then
  echo "collaboration status exposes credentials" >&2
  exit 1
fi

# Support snapshots are shareable: identifying production names and all credential-field names stay out.
if bash bin/streamerctl support | grep -E '"(currentScene|selectedSourceName|workspaceName|activeWindowClass|sensitiveRule|room|password|streamId|controlId|inviteUrl|programUrl|directorUrl)"'; then
  echo "support snapshot exposes a forbidden field" >&2
  exit 1
fi

# Onboarding/profile/settings status models must remain free of streaming/collaboration secrets.
for cmd in 'python3 bin/onboardingctl.py status' 'python3 bin/profilectl.py status' 'python3 bin/settings.py status'; do
  if eval "$cmd" | grep -E '"(room|password|streamId|controlId|inviteUrl|programUrl|directorUrl)"'; then
    echo "safe status unexpectedly exposes sensitive fields: $cmd" >&2
    exit 1
  fi
done

grep -q 'function open(payload)' Onboarding.qml
grep -q 'FIRST-RUN GUIDE' Onboarding.qml
grep -q 'docs/USER_GUIDE.md' Onboarding.qml
grep -q 'collab.guest-disconnect' BarWidget.qml
grep -q 'guestRefreshTimer' Service.qml
grep -q 'profileGuestLayout' Service.qml
grep -q 'version: 10' Service.qml
grep -q 'support.snapshot' Service.qml
grep -q 'settings.set' Service.qml

echo "smoke tests passed"
