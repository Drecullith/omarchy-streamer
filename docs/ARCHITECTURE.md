# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming, recording, audio, privacy, collaboration, and onboarding without hidden privileged actions or permanent ownership of user settings.

The v0.7 architecture has nine main pieces:

1. `BarWidget.qml` — user-facing status and controls, including replayable Guide access.
2. `Onboarding.qml` — native Quattro overlay for first-run guidance, preflight, and replayable help.
3. `Service.qml` — long-lived Quickshell service, IPC boundary, and one-time first-run summon.
4. `bin/streamerctl` — action router, reversible mode/privacy state, composite emergency actions, and onboarding summon path.
5. `bin/obsws.py` — authenticated localhost OBS WebSocket v5 adapter.
6. `bin/obsbrowser.py` — non-destructive OBS Browser Source provisioning.
7. `bin/audioctl.py` / `bin/safetyctl.py` — WirePlumber audio and Hyprland stream-safety adapters.
8. `bin/collabctl.py` — browser collaboration rooms, managed guest identities, secret-link handling, and OBS collaboration source orchestration.
9. `bin/onboardingctl.py` — tiny user-only onboarding completion state.

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
- Collaboration room passwords, managed stream IDs, page-control IDs, and secret URLs are never included in generic status or IPC snapshots.
- Secret-bearing collaboration actions are explicit and confirmation-marked.
- Managed OBS Browser Sources never overwrite a non-Browser Source with the same reserved name.
- Onboarding status contains no stream/collaboration credentials.
- Skipping onboarding suppresses repeat first-run summons rather than nagging every login.

## Plugin kinds and lifecycle

The manifest declares three kinds:

```text
service
bar-widget
overlay
```

The service and bar widget stay available as before. `Onboarding.qml` is registered as the plugin overlay and uses Omarchy's normal `shell summon` lifecycle.

On service startup:

1. `streamerctl status` includes safe onboarding state.
2. If the current tour version is incomplete, `Service.qml` arms a short delayed first-run timer.
3. The service invokes `onboarding.open first-run` once for that shell session.
4. `streamerctl` asks `omarchy-shell shell summon io.github.drecullith.streamer` to show the registered overlay.
5. Skip/Finish calls `onboarding.complete`, which writes the completion marker.

The delay avoids racing plugin registration during shell startup. The service deliberately marks the summon attempted for that shell session rather than repeatedly opening the guide if the user is interacting with the desktop.

## Onboarding state

Onboarding state is stored under the normal Streamer state root:

```text
$XDG_STATE_HOME/omarchy-streamer/onboarding.json
```

or `~/.local/state/omarchy-streamer/onboarding.json`.

The file contains only:

```text
version
completedAt
```

It is written with user-only permissions where supported.

The current safe status model exposes:

```text
ready
tourVersion
completed
completedAt
error
```

A future tour version can become eligible automatically by increasing the internal tour version without deleting unrelated Streamer state.

## Guided overlay

`Onboarding.qml` follows the same overlay lifecycle pattern as first-party Quattro overlays: `open(payload)` reveals a layer-shell `PanelWindow`, and `close()` hides it.

Supported modes:

```text
first-run  start at Welcome and require Skip/Finish to suppress future first-run summon
tour       replay the guide without changing completion state
preflight  open directly on the live preflight page
```

The overlay has seven pages covering the safety model, preflight, OBS, Audio Desk, Stream-Safe/emergency controls, collaboration, and a ready-to-stream checklist.

The preflight page queries the normal `streamerctl status` path. It does not introduce a second privileged configuration path.

## Runtime state

General state lives under:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Persisted state includes reversible Streamer Mode/privacy state, Audio Desk mic selection, previous Stream-Safe workspace, collaboration session credentials, and onboarding completion.

Sensitive state files are written with user-only permissions where supported. OBS output state remains authoritative in OBS and is queried live.

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

Onboarding actions:

```text
onboarding.open <tour|first-run|preflight>
onboarding.complete
onboarding.reset
```

The action vocabulary is defined in `contracts/actions-v1.json`. High-impact actions remain explicitly marked so external callers can require confirmation before invocation.

## OBS integration

`obsws.py` speaks OBS WebSocket v5 using Python's standard library, keeps authentication enabled, defaults to localhost, and stores no stream-service credentials.

`obsbrowser.py` builds on that client for collaboration Browser Sources.

Provisioning flow:

```text
collabctl.py
    │ secret provider URL held in process memory
    ▼
obsbrowser.py
    │ authenticated request
    ▼
obs-websocket
    │
    ├── ensure dedicated scene exists
    ├── create Browser Source if missing
    ├── update managed Browser Source settings if it exists
    └── add existing managed Browser Source to scene if needed
```

The default collaboration scene is `Omarchy Guests`. It can be overridden through `OMARCHY_STREAMER_GUEST_SCENE`.

Reserved source names are `Omarchy Streamer - Guests` and `Omarchy Streamer - Guest N`. If a reserved name already exists as a non-`browser_source`, provisioning fails safely rather than replacing it.

## Collaboration identity model

A collaboration session has a room ID/password plus four managed guest slots by default.

Each managed slot contains a safe slot number/label plus private `streamId` and `controlId` capability values. v0.5 rooms are migrated in place so existing room/password values remain unchanged while managed slots are added.

Generic collaboration status exposes only safe metadata and deliberately excludes room, password, stream IDs, control IDs, and secret URLs.

A managed guest invite can carry its private control capability, while the corresponding solo OBS URL receives only the view identity. This prevents OBS from receiving the guest page's remote-control capability.

## Live guest-control boundary

Private guest control IDs are provisioned but live presence/mute/remove actions are not yet exposed. Those controls wait for real provider-session testing of network lifecycle, stale-state handling, and authorization behavior.

## Stream-Safe workspace

`safetyctl.py` uses explicit Hyprland workspace/window queries and dispatch. `workspace.enter` remembers the active workspace name and switches to the configured Stream-Safe workspace. `workspace.exit` restores the remembered workspace.

Sensitive-window rules are warning-only. Active titles may participate in local matching but are not serialized into status.

## Audio integration

`audioctl.py` uses WirePlumber `wpctl`. It remembers a microphone by PipeWire node name and resolves the current numeric ID on demand. Missing selected devices are surfaced rather than silently replaced.

## Emergency actions

`emergency.end-live` independently attempts Privacy/DND on, selected microphone mute, Stream-Safe workspace entry, and OBS stream stop.

`emergency.stop-all` additionally attempts recording and replay-buffer stop.

## Health model

`streamerctl status` returns version 7 state containing safe aggregate state from OBS, Audio Desk, Stream-Safe, Collaboration, and Onboarding.

Unknown/unreachable subsystems are represented explicitly rather than being presented as healthy.

## Tests

CI validates:

- manifest and action contract, including overlay registration and v0.7 version,
- shell/Python syntax,
- safe status behavior without desktop services,
- fake local OBS WebSocket RPC,
- OBS Browser Source create/update/collision behavior,
- fake WirePlumber/wpctl behavior,
- fake Hyprland workspace/window behavior,
- sensitive-window title non-disclosure,
- Stream-Safe workspace enter/restore,
- collaboration state permissions/migration/slot rotation,
- collaboration secret non-disclosure,
- onboarding initial/complete/reset/version behavior,
- onboarding state file permissions,
- onboarding status secret-field guard,
- presence of the overlay lifecycle/manual hooks,
- public documentation remaining integration-neutral.

The remaining validation class is real Omarchy Quattro + OBS + PipeWire + Hyprland + browser collaboration testing, including visual/focus validation of the new overlay.
