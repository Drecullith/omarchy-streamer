# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that turns a normal desktop session into a deliberate streaming/recording workspace without hiding privileged actions or taking permanent ownership of user settings.

The v0.3 architecture has five layers:

1. `BarWidget.qml` — user-facing status and fast controls.
2. `Service.qml` — long-lived Quickshell service and IPC boundary.
3. `bin/streamerctl` — user-level controller for mode state, health and reversible privacy changes.
4. `bin/obsws.py` — localhost OBS WebSocket v5 adapter implemented with the Python standard library.
5. `bin/audioctl.py` — WirePlumber/wpctl Audio Desk controller.

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
- A missing selected microphone is reported rather than silently replaced.
- Audio Desk selection does not silently overwrite the desktop-wide default microphone.

## State

Runtime state is stored under:

`$XDG_STATE_HOME/omarchy-streamer/`

or, when `XDG_STATE_HOME` is unset:

`~/.local/state/omarchy-streamer/`

Marker files record active mode/privacy state plus a snapshot of the notification DND state that existed before Streamer Privacy was enabled.

Audio Desk stores only the selected PipeWire source node name in `audio.json`. Numeric PipeWire node IDs are treated as ephemeral and resolved again from WirePlumber whenever status or an audio action is requested.

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

OBS Studio 28+ includes obs-websocket. Omarchy Streamer speaks its v5 JSON protocol directly.

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

### OBS authentication and connection rules

The adapter:

- reads OBS's local `plugin_config/obs-websocket/config.json` by default,
- uses OBS's configured WebSocket password for the v5 challenge/response handshake,
- never writes that password into Streamer state,
- defaults to localhost,
- rejects a non-loopback host unless `OMARCHY_STREAMER_OBS_ALLOW_REMOTE=1` is explicitly set,
- verifies the RFC 6455 WebSocket upgrade response,
- masks client frames as required by the WebSocket protocol.

## Audio Desk

PipeWire is the native audio layer and WirePlumber's `wpctl` command is the v0.3 control boundary.

Control flow:

```text
UI / IPC action
      │
      ▼
Service.qml / streamerctl
      │
      ▼
audioctl.py
      │
      ▼
wpctl
      │
      ▼
WirePlumber / PipeWire source node
```

The controller uses `wpctl list audio sources` for discovery, `wpctl get-volume` for volume/mute status, and `wpctl set-mute` / `wpctl set-volume` for control.

The selected microphone is persisted by node name rather than object ID. If that name is no longer present, status reports `selectedPresent: false` and audio actions fail visibly until the user selects another source.

Implemented Audio Desk actions:

```text
mic.select <sourceNameOrId>
mic.next
mic.mute
mic.unmute
mic.toggle
mic.volume <0-150>
```

The first Audio Desk milestone intentionally does **not** rewrite PipeWire links or force a new system default. Deeper game/browser/collaborator routing belongs after physical-device testing.

## Health model

`streamerctl status` combines local mode/dependency state with live OBS and audio state.

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
audio.ready
audio.sources
audio.selectedSourceName
audio.selectedSourceId
audio.selectedPresent
audio.muted
audio.volumePercent
audio.error
```

Unknown output/audio states are represented as `null` where appropriate rather than being presented as known-safe values.

## Privacy roadmap

v0.3 integrates with Omarchy notification DND and restores the user's prior DND state. The bar also raises a visible warning if OBS reports streaming/recording while Streamer Privacy is off.

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
- Python adapter/controller syntax,
- safe status behavior when OBS/Omarchy/PipeWire tools are absent,
- a fake local OBS WebSocket server exercising handshake + RPC,
- stream/record/replay/clip/scene actions,
- default rejection of unintended remote OBS hosts,
- a fake `wpctl` environment covering microphone discovery, selection, mute and volume,
- missing selected microphone handling without automatic substitution,
- public documentation remaining integration-neutral.

The final missing class of validation is a real Omarchy Quattro + OBS + PipeWire machine test.
