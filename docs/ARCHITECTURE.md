# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that turns a normal desktop session into a deliberate streaming/recording workspace without hiding privileged actions or taking permanent ownership of user settings.

The v0.2 architecture has four layers:

1. `BarWidget.qml` — user-facing status and fast controls.
2. `Service.qml` — long-lived Quickshell service and IPC boundary.
3. `bin/streamerctl` — user-level controller for mode state, health and reversible privacy changes.
4. `bin/obsws.py` — localhost OBS WebSocket v5 adapter implemented with the Python standard library.

## Core invariants

- No root requirement.
- No implicit `sudo`.
- No package manager invocation.
- Missing dependencies are reported, not silently installed.
- State changed by Streamer Mode must be restorable when the mode is disabled.
- Broadcast-affecting actions have stable names and are exposed through one action contract.
- External automation must call the same explicit actions as the UI; it receives no hidden privileged path.
- High-impact actions remain identifiable in the contract so callers can require confirmation before invoking them.
- Stream keys and streaming-service credentials are not stored by Omarchy Streamer.

## State

Runtime state is stored under:

`$XDG_STATE_HOME/omarchy-streamer/`

or, when `XDG_STATE_HOME` is unset:

`~/.local/state/omarchy-streamer/`

Marker files record active mode/privacy state plus a snapshot of the notification DND state that existed before Streamer Privacy was enabled.

This makes notification suppression reversible. If DND was already on before Streamer Mode, disabling Streamer Mode leaves it on.

OBS state is **not** persisted as authoritative state. Stream/record/replay/scene state is queried from OBS itself.

## IPC

The Quickshell service registers:

`io.github.drecullith.streamer`

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

The stable action vocabulary is documented in `contracts/actions-v1.json`.

The UI and external integrations share this same boundary. There is no separate unrestricted automation route.

## OBS integration

OBS Studio 28+ includes obs-websocket. v0.2 speaks its v5 JSON protocol directly.

Control flow:

```text
UI / IPC action
      │
      ▼
Service.qml / streamerctl
      │
      ▼
obsws.py
      │
      ▼
127.0.0.1:4455 (default)
      │
      ▼
OBS Studio
```

Implemented requests include:

- `GetStreamStatus`, `StartStream`, `StopStream`
- `GetRecordStatus`, `StartRecord`, `StopRecord`
- `GetReplayBufferStatus`, `StartReplayBuffer`, `StopReplayBuffer`, `SaveReplayBuffer`
- `GetSceneList`, `SetCurrentProgramScene`

`GetSceneList` is used for current-scene status rather than depending on a separate current-program-scene query.

### OBS authentication and connection rules

The adapter:

- reads OBS's local `plugin_config/obs-websocket/config.json` by default,
- uses OBS's configured WebSocket password for the v5 challenge/response handshake,
- never writes that password into Streamer state,
- defaults to localhost,
- rejects a non-loopback host unless `OMARCHY_STREAMER_OBS_ALLOW_REMOTE=1` is explicitly set,
- verifies the RFC 6455 WebSocket upgrade response,
- masks client frames as required by the WebSocket protocol.

Environment overrides exist for advanced/testing use:

```text
OMARCHY_STREAMER_OBS_CONFIG
OMARCHY_STREAMER_OBS_HOST
OMARCHY_STREAMER_OBS_PORT
OMARCHY_STREAMER_OBS_PASSWORD
OMARCHY_STREAMER_OBS_TIMEOUT
OMARCHY_STREAMER_OBS_ALLOW_REMOTE
```

## Health model

`streamerctl status` combines local mode/dependency state with live OBS state.

Important fields include:

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
obsWebSocket.connected
obsWebSocket.streaming
obsWebSocket.recording
obsWebSocket.replayBuffer
obsWebSocket.currentScene
obsWebSocket.error
```

Unknown OBS output states are represented as `null`, not `false`, when the WebSocket cannot be queried. This avoids presenting an unreachable OBS instance as definitely idle.

## Audio roadmap

PipeWire is the native audio layer. v0.3 will add explicit device/node identities and should support:

- microphone mute/unmute
- microphone selection
- per-source monitoring
- collaborator/game/browser routing
- health warnings when a configured source disappears

## Privacy roadmap

v0.2 integrates with Omarchy notification DND and restores the user's prior DND state. The bar also raises a visible warning if OBS reports streaming/recording while Streamer Privacy is off.

Later protections may include:

- notification-history suppression during capture
- stream-safe workspaces
- sensitive-window warnings
- clipboard-popup suppression
- optional screen-share allowlists
- emergency stop/mute controls

Privacy protections should fail safe and visibly report when a requested protection could not be applied.

## Collaboration

Collaboration is adapter-based rather than a hard dependency on one communications product. The core should expose collaborator presence and room controls in a way that browser guests, Mode700, or other collaboration tools can use without changing Streamer Mode's lifecycle.

## Tests

CI currently validates:

- manifest and action-contract JSON,
- controller shell syntax,
- Python adapter syntax,
- safe status behavior when OBS/Omarchy services are absent,
- a fake local OBS WebSocket server exercising handshake + RPC,
- coalesced HTTP-upgrade and first WebSocket-frame handling,
- stream/record/replay/clip/scene actions,
- default rejection of unintended remote OBS hosts,
- public documentation remaining integration-neutral.

The final missing class of validation is a real Omarchy Quattro + OBS + PipeWire machine test.
