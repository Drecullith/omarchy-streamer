# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming, recording, audio, privacy, collaboration, guest control, and onboarding without hidden privileged actions or permanent ownership of user settings.

The v0.8 architecture has ten main pieces:

1. `BarWidget.qml` — user-facing status and controls, including managed guest state/control and replayable Guide access.
2. `Onboarding.qml` — native Quattro overlay for first-run guidance, preflight, and replayable help.
3. `Service.qml` — long-lived Quickshell service, IPC boundary, one-time first-run summon, and bounded guest-presence refresh loop.
4. `bin/streamerctl` — action router, reversible mode/privacy state, composite emergency actions, onboarding summon path, and collaboration action boundary.
5. `bin/obsws.py` — authenticated localhost OBS WebSocket v5 adapter.
6. `bin/obsbrowser.py` — non-destructive OBS Browser Source provisioning.
7. `bin/audioctl.py` / `bin/safetyctl.py` — WirePlumber audio and Hyprland stream-safety adapters.
8. `bin/collabctl.py` — browser rooms, managed guest identities, safe guest-state cache, secret-link handling, provider-control orchestration, and OBS collaboration source orchestration.
9. `bin/vdoapi.py` — minimal VDO.Ninja private page-control WebSocket client with correlated callbacks and explicit timeouts.
10. `bin/onboardingctl.py` — tiny user-only onboarding completion state.

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
- Private page-control IDs are not passed as process command-line arguments.
- Secret-bearing collaboration actions and remote guest mutations are explicit and confirmation-marked.
- A provider WebSocket connection alone never counts as guest presence.
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

The service is the long-running coordinator. The bar widget reads safe status and invokes explicit actions. `Onboarding.qml` is registered as the plugin overlay and uses Omarchy's normal `shell summon` lifecycle.

On service startup, onboarding state is checked and the first-run guide is summoned once when eligible. While a collaboration room with managed slots is active, the service also runs the guest refresh action every 15 seconds. The bar/status path itself does not perform provider network I/O; it reads the local guest-state cache.

## Runtime state

General state lives under:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Persisted state includes reversible Streamer Mode/privacy state, Audio Desk mic selection, previous Stream-Safe workspace, collaboration session credentials, cached safe guest state, and onboarding completion.

Sensitive state files are written with user-only permissions where supported. The collaboration session file contains room/slot capabilities. The guest-state cache contains only safe fields and no credentials.

OBS output state remains authoritative in OBS and is queried live.

## Onboarding state and overlay

Onboarding state is stored in:

```text
$XDG_STATE_HOME/omarchy-streamer/onboarding.json
```

The file contains only `version` and `completedAt`.

`Onboarding.qml` supports:

```text
first-run
 tour
preflight
```

The preflight page queries the same normal `streamerctl status` path used elsewhere. It does not create a second privileged configuration path.

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

The action vocabulary is defined in `contracts/actions-v1.json`. High-impact actions are marked so external callers can require confirmation before invocation.

Remote guest mutations are high-impact actions:

```text
collab.guest-mute <slot>
collab.guest-unmute <slot>
collab.guest-disconnect <slot>
```

Presence refresh is read-only:

```text
collab.guest-refresh
```

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

The default collaboration scene is `Omarchy Guests`, overridable through `OMARCHY_STREAMER_GUEST_SCENE`.

Reserved source names are `Omarchy Streamer - Guests` and `Omarchy Streamer - Guest N`. If a reserved name already exists as a non-`browser_source`, provisioning fails safely rather than replacing it.

## Collaboration identity model

A collaboration session has a room ID/password plus four managed guest slots by default.

Each managed slot contains:

```text
slot number       safe UI identity
label             local human-facing label
streamId          private publish/view identity
controlId         private page-control capability
```

A managed guest invite can carry its private control capability, while the corresponding solo OBS URL receives only the view identity. This prevents OBS from receiving the guest page's remote-control capability.

v0.5 rooms are migrated in place so existing room/password values remain unchanged while managed slots are added.

## Provider page-control boundary

`vdoapi.py` speaks the provider's documented private page-control WebSocket interface.

For one request it:

1. opens `wss://api.vdo.ninja/` by default,
2. joins the private `controlId`,
3. sends one explicit action with a unique callback ID (`cib`),
4. ignores unrelated messages,
5. accepts only the callback carrying the matching `cib`,
6. times out instead of assuming success.

The default callback timeout is 1.4 seconds and can be overridden with `OMARCHY_STREAMER_VDO_API_TIMEOUT`. The endpoint can be overridden with `OMARCHY_STREAMER_VDO_API_URL`; CI uses a local plain-WebSocket fake provider.

Private `controlId` values are loaded by `collabctl.py` from the user-only session file and passed directly to the imported `vdoapi` module in memory. They are not supplied as CLI arguments.

## Guest presence model

Presence is deliberately callback-based.

A slot is **ONLINE** only when its own managed page answers a correlated `getDetails` callback. Merely opening the provider API WebSocket does not prove page presence.

A missing callback within the timeout produces **OFFLINE**. A control-channel connection failure produces an unknown/control-unavailable state rather than an invented offline result.

Safe cached state contains only:

```text
slot
online
micEnabled
checkedAt
stale
error
```

The cache is stored as `collab-guest-state.json` with user-only permissions where supported. `stale` becomes true after 30 seconds by default.

Four slot probes run concurrently, while cache read-modify-write operations are serialized so one guest update cannot clobber another guest's state.

## Guest remote controls

`collab.guest-mute` and `collab.guest-unmute` send the documented `mic` page action and wait for the correlated callback. The cached `micEnabled` field changes only from a returned boolean callback result.

`collab.guest-disconnect` sends the documented `hangup` page action and marks the slot offline only after the command callback is received.

Timeouts and connection failures surface as errors; they are not converted into success.

These paths are protocol-tested in CI against a local fake WebSocket provider. Real VDO.Ninja browser-session behavior remains a field-validation item and should not be described as hardware/session verified yet.

## Stream-Safe workspace

`safetyctl.py` uses explicit Hyprland workspace/window queries and dispatch. `workspace.enter` remembers the active workspace name and switches to the configured Stream-Safe workspace. `workspace.exit` restores the remembered workspace.

Sensitive-window rules are warning-only. Active titles may participate in local matching but are not serialized into status.

## Audio integration

`audioctl.py` uses WirePlumber `wpctl`. It remembers a microphone by PipeWire node name and resolves the current numeric ID on demand. Missing selected devices are surfaced rather than silently replaced.

Per-guest PipeWire routing is not implemented yet because it requires real browser-source/audio-session observation to map provider streams to local audio nodes safely.

## Emergency actions

`emergency.end-live` independently attempts Privacy/DND on, selected microphone mute, Stream-Safe workspace entry, and OBS stream stop.

`emergency.stop-all` additionally attempts recording and replay-buffer stop.

## Health model

`streamerctl status` returns version 8 state containing safe aggregate state from OBS, Audio Desk, Stream-Safe, Collaboration, guest-state cache, and Onboarding.

Unknown/unreachable subsystems are represented explicitly rather than being presented as healthy.

## Tests

CI validates:

- manifest and action contract, including v0.8 version,
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
- parallel four-slot guest refresh without cache clobbering,
- callback-backed mic state and disconnect cache transitions,
- timeout-is-not-online behavior,
- VDO.Ninja-style WebSocket join/action/callback correlation against a fake provider,
- onboarding initial/complete/reset/version behavior,
- onboarding state file permissions and secret-field guard,
- presence of overlay/manual hooks,
- public documentation remaining integration-neutral.

The remaining validation class is real Omarchy Quattro + OBS + PipeWire + Hyprland + browser collaboration testing, including visual/focus validation of the overlay and real provider page-control behavior.