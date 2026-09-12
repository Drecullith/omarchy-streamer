# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace with OBS control, PipeWire-aware audio controls, reversible privacy protection, stream-safe workspace tools, emergency actions, and a stable local action surface for future integrations.

> Status: early **v0.4**. Core lifecycle, authenticated OBS control, Audio Desk, Stream-Safe workspace controls, sensitive-window warnings, emergency actions, health state, bar UI, IPC, and CI coverage are in place. Real Omarchy/OBS/PipeWire hardware validation is still required.

## Current v0.4

- Omarchy Quattro third-party plugin
- bar widget + popup control panel
- long-running service and explicit IPC target
- reversible Streamer Mode + notification DND state
- authenticated OBS WebSocket v5 control
- live stream / recording / replay-buffer / clip / scene controls
- LIVE / REC bar state from OBS
- PipeWire / WirePlumber Audio Desk
- remembered microphone selection without changing the desktop default
- mic mute/unmute/toggle and volume controls
- missing-microphone warnings
- dedicated named **Stream-Safe** Hyprland workspace
- remembers and restores the workspace you came from
- warning-only sensitive-window guard
- default warnings for common password/authenticator apps
- user-extensible sensitive-app rules
- emergency **End Live + Mute**
- emergency **Stop All Capture**
- no root requirement
- no implicit `sudo`
- no automatic package installation
- no stream keys stored by the plugin
- CI tests for manifest, contracts, OBS RPC, Audio Desk, and Stream-Safe behavior

## Install on Omarchy Quattro

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

### Runtime requirements

- Omarchy Quattro
- OBS Studio 28+ (obs-websocket is built in)
- Python 3 for the local controllers
- PipeWire + WirePlumber `wpctl` for Audio Desk
- Hyprland `hyprctl` for Stream-Safe workspace/window checks

Missing requirements are reported. Omarchy Streamer does not silently install them.

## Controls

Left-click **Stream** on the bar to open the panel. Right-click toggles Streamer Mode.

The panel exposes Streamer Mode, stream/record/replay/clip/scene controls, Audio Desk, Stream-Safe workspace controls, privacy status, sensitive-window warnings, and emergency buttons.

### Emergency actions

`emergency.end-live` performs a best-effort safety sequence:

1. enable Streamer Privacy / DND,
2. mute the selected microphone,
3. switch into the Stream-Safe workspace,
4. stop the live stream.

`emergency.stop-all` performs the same sequence and also stops recording and the replay buffer.

Emergency actions are deliberately best-effort: one unavailable subsystem does not prevent the remaining safety steps from being attempted.

## Stream-Safe workspace

`workspace.enter` records the current Hyprland workspace by **name** and switches to the dedicated `stream-safe` named workspace. It does **not** move, close, hide, or kill any windows.

`workspace.exit` returns to the previously recorded workspace.

The workspace name can be overridden with:

```text
OMARCHY_STREAMER_SAFE_WORKSPACE
```

The plugin avoids persisting Hyprland workspace IDs because named-workspace IDs may be reassigned between sessions.

## Sensitive-window warnings

The active Hyprland window is checked against warning rules. Matching is case-insensitive and **warning-only**; Omarchy Streamer never takes destructive action against a matched application.

Built-in rules live in:

```text
config/sensitive-apps.txt
```

Personal rules can be added without editing the plugin:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

Rule formats:

```text
class:bitwarden
title:password manager
any:my-sensitive-app
```

Window titles are used locally for matching but are not returned in Streamer status.

## Audio Desk

Audio Desk uses WirePlumber `wpctl`, remembers the selected microphone by PipeWire node name, and re-resolves its current object ID. Selecting a mic in Streamer does not silently replace the system-wide default microphone.

Actions:

```text
mic.select <sourceNameOrId>
mic.next
mic.mute
mic.unmute
mic.toggle
mic.volume <0-150>
```

## IPC

The service exposes:

```text
io.github.drecullith.streamer
```

Examples:

```bash
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer action stream.start ""
omarchy-shell io.github.drecullith.streamer action mic.mute ""
omarchy-shell io.github.drecullith.streamer action workspace.enter ""
omarchy-shell io.github.drecullith.streamer action emergency.end-live ""
```

The stable action vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). The UI and external integrations use the same named action boundary.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
BarWidget.qml
      │
Service.qml ── IPC
      │
      └── bin/streamerctl
             ├── bin/obsws.py     ── localhost OBS WebSocket v5
             ├── bin/audioctl.py  ── WirePlumber/wpctl Audio Desk
             └── bin/safetyctl.py ── Hyprland workspace/window safety
```

## Roadmap

### v0.5 — Collaboration

- collaborator room workflow
- browser guest integration
- guest mute/remove and individual audio controls
- deeper game/browser/collaborator PipeWire routing
- later Mode700 integration

### Later — Stream profiles and integrations

- Gaming / Recording / Podcast / low-spec presets
- more capture-source awareness
- configurable safety profiles
- external local integrations through the existing action contract

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, silently substitute a missing selected microphone, auto-close sensitive apps, clear the clipboard, or hand external automation unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
