# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming, recording, audio, privacy, and collaboration without hidden privileged actions or permanent ownership of user settings.

The v0.6 architecture has seven main pieces:

1. `BarWidget.qml` — user-facing status and controls.
2. `Service.qml` — long-lived Quickshell service and IPC boundary.
3. `bin/streamerctl` — action router, reversible mode/privacy state, and composite emergency actions.
4. `bin/obsws.py` — authenticated localhost OBS WebSocket v5 adapter.
5. `bin/obsbrowser.py` — non-destructive OBS Browser Source provisioning.
6. `bin/audioctl.py` / `bin/safetyctl.py` — WirePlumber audio and Hyprland stream-safety adapters.
7. `bin/collabctl.py` — browser collaboration rooms, managed guest identities, secret-link handling, and OBS collaboration source orchestration.

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

## Runtime state

State is stored under:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Persisted state includes reversible control state such as Streamer Mode, privacy/DND restoration, Audio Desk mic selection, previous Stream-Safe workspace, and collaboration session credentials.

Collaboration state files are written with user-only permissions where supported. OBS output state remains authoritative in OBS and is queried live.

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

The action vocabulary is defined in `contracts/actions-v1.json`. High-impact actions are explicitly marked so external callers can require confirmation before invocation.

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

The default collaboration scene is:

```text
Omarchy Guests
```

It can be overridden through `OMARCHY_STREAMER_GUEST_SCENE`.

Reserved source names are:

```text
Omarchy Streamer - Guests
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
...
```

If one of these names already exists as a non-`browser_source`, provisioning fails safely rather than replacing it.

## Collaboration identity model

A collaboration session has a room ID/password plus managed guest slots.

Each managed slot contains:

```text
slot number       safe UI identity
label             local human-facing label
streamId          private VDO.Ninja publish/view identity
controlId         private page-control capability
```

v0.6 creates four managed slots by default. A v0.5 room is migrated in place: its room/password remain unchanged while slot identities are generated and added.

The generic collaboration status exposes only safe metadata:

```text
active
provider
providerLabel
clipboardReady
browserReady
inviteReady
programUrlReady
managedSlotsReady
slotCount
obsSceneName
credentialsExposed=false
error
```

It deliberately excludes room, password, stream IDs, control IDs, and secret URLs.

## Managed guest links

A managed guest invite contains the room/password, a stable per-slot publish ID, human label, and a private page-control ID.

The corresponding solo OBS URL contains the room/password and the slot's stable stream ID but not the page-control ID.

This separation lets OBS view a guest without receiving that guest page's remote-control capability.

`collab.slot-rotate <N>` regenerates only slot N's stream/control identities. The room and other guest slots remain unchanged.

`collab.rotate` replaces the entire room and all managed slot credentials.

## Live guest-control boundary

VDO.Ninja's documented page-control API treats possession of an `api` ID as a control capability, not a read-only identity.

v0.6 therefore provisions unique private control IDs but does not yet expose live presence/mute/remove actions. Those controls will be implemented only after their network lifecycle, stale-state handling, and authorization behavior are verified in a real collaboration session.

## Stream-Safe workspace

`safetyctl.py` uses explicit Hyprland workspace/window queries and dispatch. `workspace.enter` remembers the active workspace name and switches to the configured `stream-safe` named workspace. `workspace.exit` restores the remembered workspace.

Sensitive-window rules are warning-only. Active titles may participate in local matching but are not serialized into status.

## Audio integration

`audioctl.py` uses WirePlumber `wpctl`. It remembers a microphone by PipeWire node name and resolves the current numeric ID on demand. Missing selected devices are surfaced rather than silently replaced.

## Emergency actions

`emergency.end-live` attempts independently:

- Streamer Privacy/DND on,
- selected microphone mute,
- Stream-Safe workspace entry,
- OBS stream stop.

`emergency.stop-all` additionally attempts recording and replay-buffer stop.

## Health model

`streamerctl status` returns version 6 state containing safe aggregate state from OBS, Audio Desk, Stream-Safe, and Collaboration.

Unknown/unreachable subsystems are represented explicitly rather than being presented as healthy.

## Tests

CI validates:

- manifest and action contract,
- shell/Python syntax,
- safe status behavior without desktop services,
- fake local OBS WebSocket RPC,
- OBS Browser Source create/update/collision behavior,
- fake WirePlumber/wpctl behavior,
- fake Hyprland workspace/window behavior,
- sensitive-window title non-disclosure,
- Stream-Safe workspace enter/restore,
- collaboration state permissions,
- v0.5 collaboration-session migration,
- managed slot identity/link generation,
- single-slot rotation isolation,
- collaboration secret non-disclosure,
- safe handoff of secret provider URLs to the OBS source adapter,
- public documentation remaining integration-neutral.

The remaining validation class is real Omarchy Quattro + OBS + PipeWire + Hyprland + browser collaboration hardware/session testing.

## Planned onboarding layer

A dedicated user guide and guided first-run experience is planned next. It will sit above the same status/action contract rather than creating a second hidden configuration path.
