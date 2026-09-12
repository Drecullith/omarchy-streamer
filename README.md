# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace: OBS orchestration, PipeWire-aware audio control, reversible privacy protection, recording/streaming controls, collaborator workflows, and a stable action surface for future integrations and automation.

> Status: early **v0.3**. Streamer Mode lifecycle, privacy, OBS WebSocket control, Audio Desk, health state, bar UI, IPC, and the action contract are in place. Deeper per-application routing and stream-safe workspace protection remain future work.

## Current v0.3

- Omarchy Quattro third-party plugin
- bar widget + popup control panel
- long-running service and explicit IPC target
- Streamer Mode enable/disable/toggle
- reversible notification privacy using Omarchy DND
- preserves the user's previous DND state
- OBS Studio detection and launch
- authenticated OBS WebSocket v5 control
- live stream start/stop
- recording start/stop
- replay buffer start/stop and save clip
- current-scene status and scene switching
- LIVE / REC bar state based on OBS, not just local mode state
- warning when capture is active while Streamer Privacy is off
- PipeWire / WirePlumber Audio Desk
- microphone discovery and remembered selection
- microphone mute/unmute/toggle
- microphone volume control
- missing-microphone warning without silently substituting another source
- stable action contract for future integrations and automation
- no root requirement
- no implicit `sudo`
- no automatic package installation
- no stream keys stored by the plugin
- CI tests for manifest, controller, action contract, OBS WebSocket RPC, and Audio Desk behavior

## Install on Omarchy Quattro

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

### Runtime requirements

- Omarchy Quattro
- OBS Studio 28+ (obs-websocket is built in)
- Python 3 for the small local protocol/controllers
- PipeWire + WirePlumber `wpctl` for Audio Desk

Omarchy Streamer **detects** missing requirements. It does not silently install them.

## Controls

Left-click the **Stream** bar widget to open the control popup.

Right-click the widget to toggle Streamer Mode quickly.

The popup currently provides:

- Streamer Mode on/off
- OBS launch
- Stream start/stop
- Recording start/stop
- Replay buffer start/stop
- Save Clip
- Set Scene
- microphone selection/cycling
- microphone mute/unmute
- microphone volume ±5%
- Privacy on/off
- OBS/PipeWire/audio/privacy health

When OBS reports a live stream the bar shows **LIVE**. During local recording it shows **REC**.

## Audio Desk

Audio Desk uses WirePlumber's `wpctl` interface. It discovers audio source nodes, remembers the chosen microphone by its PipeWire node name, and resolves the current node ID each time.

This matters because PipeWire numeric object IDs may change between sessions or reconnects.

Selecting a microphone in Omarchy Streamer **does not silently change the desktop-wide default microphone**. The chosen source is the one Streamer controls directly. If a previously selected microphone disappears, Streamer reports it as missing rather than quietly switching to another source.

Available Audio Desk actions include:

```text
mic.select <sourceNameOrId>
mic.next
mic.mute
mic.unmute
mic.toggle
mic.volume <0-150>
```

Deeper game/browser/collaborator routing is planned after real-hardware validation.

## Streamer Privacy

Streamer Mode currently:

1. records that the mode is active,
2. captures the current Omarchy notification DND state,
3. enables DND for stream privacy,
4. restores the captured DND state when Streamer Mode is disabled.

If DND was already enabled before Streamer Mode, it stays enabled afterward. If Omarchy DND cannot actually be applied, the plugin does **not** claim privacy is active.

This is the first privacy layer, not the final one. Stronger capture/workspace protections are planned.

## OBS WebSocket security

The OBS adapter speaks the OBS WebSocket v5 protocol directly using Python's standard library. It does not require a third-party Python package.

By default it:

- connects only to localhost,
- reads the port/password from OBS's own local obs-websocket configuration,
- supports OBS WebSocket authentication,
- does not copy the WebSocket password into this repository or Streamer state,
- does not store streaming-service keys.

Remote OBS hosts are blocked by default. Advanced users can explicitly opt in with `OMARCHY_STREAMER_OBS_ALLOW_REMOTE=1` and connection environment variables.

## IPC

The service exposes:

```text
io.github.drecullith.streamer
```

Examples:

```bash
omarchy-shell io.github.drecullith.streamer ping
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer enable
omarchy-shell io.github.drecullith.streamer disable
omarchy-shell io.github.drecullith.streamer action stream.start ""
omarchy-shell io.github.drecullith.streamer action scene.set "BRB"
omarchy-shell io.github.drecullith.streamer action mic.mute ""
```

The stable automation vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). User UI and future integrations should use the same named actions rather than separate hidden control paths.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
BarWidget.qml
      │
      ├── user controls/status
      │
Service.qml ── IPC ── external integrations
      │
      └── bin/streamerctl
              ├── reversible privacy state
              ├── bin/obsws.py   ── localhost OBS WebSocket v5
              └── bin/audioctl.py ── WirePlumber/wpctl Audio Desk
```

## Roadmap

### v0.4 — Stream-safe workspace

- stronger notification/privacy controls
- sensitive-window warnings
- optional capture allowlists
- stream-safe workspace/profile behavior
- emergency stop/mute controls
- deeper PipeWire routing for game/browser/collaborator sources

### v0.5 — Collaboration

- collaborator room workflow
- browser guest integration
- later Mode700 integration

### Later — External integrations

The IPC/action contract is intentionally stable so other local tools can inspect Streamer Mode health and request explicit actions without receiving unrestricted shell access.

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, modify firewall rules, store stream keys, silently replace a missing selected microphone, or hand external automation unrestricted command execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
