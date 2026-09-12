# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming and recording without hidden privileged actions or permanent ownership of user settings.

The v0.4 architecture has five main pieces:

1. `BarWidget.qml` — user-facing status and controls.
2. `Service.qml` — long-lived Quickshell service and IPC boundary.
3. `bin/streamerctl` — action router, reversible mode/privacy state, and composite emergency actions.
4. `bin/obsws.py` — localhost OBS WebSocket v5 adapter.
5. `bin/audioctl.py` / `bin/safetyctl.py` — WirePlumber audio and Hyprland stream-safety adapters.

## Core invariants

- No root requirement or implicit `sudo`.
- No package-manager invocation.
- Missing dependencies are reported rather than installed.
- State changed by Streamer Mode should be restorable.
- UI and external integrations call the same explicit action contract.
- Stream keys and streaming-service credentials are not stored.
- Sensitive-window detection is warning-only.
- Stream-Safe never auto-moves, closes, hides, or kills user windows.
- Window titles are not exposed in status output.
- Emergency actions continue best-effort when one subsystem is unavailable.

## Runtime state

State is stored under:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Current persisted state is limited to reversible control state such as Streamer Mode, privacy/DND restoration, Audio Desk mic selection, and the previous workspace used for Stream-Safe return.

OBS output state remains authoritative in OBS and is queried live.

## IPC and action mediation

The Quickshell service registers:

```text
io.github.drecullith.streamer
```

Primary calls:

```text
ping
status
refresh
action <action-name> <optional-arg>
enable
disable
toggle
```

The action vocabulary is defined in `contracts/actions-v1.json`. High-impact actions are explicitly marked so an external caller can require confirmation before invocation.

## Stream-Safe workspace

`safetyctl.py` uses `hyprctl activeworkspace -j`, `hyprctl activewindow -j`, and explicit workspace dispatch.

On `workspace.enter`:

1. read the active workspace **name**,
2. persist it with user-only file permissions where possible,
3. switch to `name:stream-safe` (or the configured safe workspace).

On `workspace.exit`, the recorded workspace is restored.

Workspace names are used instead of persisted Hyprland IDs because named-workspace IDs are not stable across sessions.

## Sensitive-window guard

Rules are plain, case-insensitive substrings scoped to `class`, `title`, or `any`.

Sources:

```text
config/sensitive-apps.txt
~/.config/omarchy-streamer/sensitive-apps.txt
```

The active title can participate in local matching, but status only returns the active class and matched rule. This avoids serializing potentially sensitive title text into Streamer health state.

A match raises a warning only. It does not manipulate the application.

## Emergency actions

`emergency.end-live` attempts, independently:

- Streamer Privacy/DND on,
- selected microphone mute,
- Stream-Safe workspace entry,
- OBS stream stop.

`emergency.stop-all` additionally attempts recording and replay-buffer stop.

The actions are intentionally best-effort. They do not abort the entire sequence because one adapter is unavailable.

## OBS integration

OBS Studio 28+ includes obs-websocket. `obsws.py` speaks the v5 protocol directly using Python's standard library, keeps OBS password authentication intact, defaults to localhost, and stores no stream keys.

## Audio integration

`audioctl.py` uses WirePlumber `wpctl`. It remembers a microphone by PipeWire node name and resolves the current numeric ID on demand. Missing selected devices are surfaced rather than silently replaced.

## Health model

`streamerctl status` returns version 4 state containing:

```text
active
privacy
obsInstalled
obsRunning
pipewireReady
wpctlInstalled
pythonReady
dndState
dndManaged
obsWebSocket.*
audio.*
safety.ready
safety.workspaceName
safety.streamSafeActive
safety.sensitiveActive
safety.sensitiveRule
safety.activeWindowClass
safety.error
```

Unknown/unreachable subsystems are represented explicitly rather than being presented as healthy.

## Tests

CI validates:

- manifest and action contract,
- shell/Python syntax,
- safe status behavior without desktop services,
- fake local OBS WebSocket RPC,
- fake WirePlumber/wpctl behavior,
- fake Hyprland workspace/window behavior,
- sensitive-window title non-disclosure,
- Stream-Safe workspace enter/restore,
- public documentation remaining integration-neutral.

The remaining validation class is real Omarchy Quattro + OBS + PipeWire + Hyprland hardware testing.
