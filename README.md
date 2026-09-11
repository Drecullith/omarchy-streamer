# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer is designed to turn an Omarchy desktop into a deliberate creator/streaming workspace: OBS orchestration, PipeWire-aware audio health, privacy protection, recording/streaming controls, collaborator workflows, and a stable action surface for future integrations and automation.

> Status: early **v0.1 baseline**. The lifecycle, privacy layer, OBS detection/launch, health model, bar UI, IPC boundary, and action contract are in place. Direct OBS stream/record/scene automation is intentionally stubbed until the audited OBS WebSocket adapter lands.

## Current v0.1

- Omarchy Quattro third-party plugin
- bar widget + popup control panel
- long-running service
- explicit IPC target: `io.github.drecullith.streamer`
- Streamer Mode enable/disable/toggle
- reversible notification privacy using Omarchy DND
- preserves the user's previous DND state
- OBS Studio detection and launch
- PipeWire and `wpctl` health detection
- stable action contract for future integrations and automation
- no root requirement
- no implicit `sudo`
- no automatic package installation
- CI smoke tests for the manifest, action contract, and controller

## Install on Omarchy Quattro

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

## Controls

Left-click the **Stream** bar widget to open the control popup.

Right-click the widget to toggle Streamer Mode quickly.

Streamer Mode currently:

1. records that the mode is active,
2. captures the current Omarchy notification DND state,
3. enables DND for stream privacy,
4. restores the captured DND state when Streamer Mode is disabled.

If DND was already enabled before Streamer Mode, it stays enabled afterward.

## IPC

The service exposes the target:

```text
io.github.drecullith.streamer
```

Examples:

```bash
omarchy-shell io.github.drecullith.streamer ping
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer enable
omarchy-shell io.github.drecullith.streamer disable
omarchy-shell io.github.drecullith.streamer action obs.launch ""
```

The long-term automation vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). User UI and future integrations should all use the same named actions rather than separate hidden control paths.

## Planned actions

```text
mode.enable
mode.disable
mode.toggle
privacy.enable
privacy.disable
obs.launch
stream.start
stream.stop
record.start
record.stop
clip.save
scene.set <sceneName>
mic.mute
mic.unmute
health.refresh
```

Actions that can unexpectedly expose the user, start broadcasting, change a live scene, launch applications, or alter capture state are marked with explicit confirmation requirements in the contract.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

The short version:

```text
BarWidget.qml
      │
      ├── user controls/status
      │
Service.qml ── IPC ── external integrations
      │
      └── bin/streamerctl
              ├── reversible privacy state
              ├── dependency/health detection
              └── local application actions
```

## Roadmap

### v0.2 — OBS adapter

- native OBS WebSocket integration
- stream start/stop
- recording start/stop
- replay-buffer clips
- scene switching
- stream/encoder health

### v0.3 — Audio desk

- microphone selection
- mic mute/unmute
- PipeWire routing
- game/browser/collaborator source awareness
- missing-device warnings

### v0.4 — Stream-safe workspace

- stronger notification/privacy controls
- sensitive-window warnings
- optional capture allowlists
- stream-safe workspace/profile behavior

### v0.5 — Collaboration

- collaborator room workflow
- browser guest integration
- later Mode700 integration

### Later — External integrations

The IPC/action contract is intentionally stable so other local tools can inspect Streamer Mode health and request explicit actions without receiving unrestricted shell access.

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, modify firewall rules, store stream keys, or hand external automation unrestricted command execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
