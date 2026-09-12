# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace with OBS control, PipeWire-aware audio controls, reversible privacy protection, stream-safe workspace tools, browser collaboration, emergency actions, and a stable local action surface for future integrations.

> Status: early **v0.5**. Core lifecycle, authenticated OBS control, Audio Desk, Stream-Safe workspace controls, browser collaboration rooms, sensitive-window warnings, emergency actions, health state, bar UI, IPC, and CI coverage are in place. Real Omarchy/OBS/PipeWire/Hyprland hardware validation is still required.

## Current v0.5

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
- emergency **End Live + Mute** and **Stop All Capture**
- provider-based browser collaboration core
- password-protected VDO.Ninja room workflow
- explicit guest-invite copying
- explicit clean group-scene URL copying for OBS Browser Source
- local-only collaboration credential storage with restrictive file permissions
- room rotation to invalidate previously shared links
- no collaboration secrets in generic plugin status/IPC snapshots
- no root requirement
- no implicit `sudo`
- no automatic package installation
- no stream keys stored by the plugin
- CI tests for manifest, contracts, OBS RPC, Audio Desk, Stream-Safe, and collaboration behavior

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
- `xdg-open` to launch a browser collaboration director
- `wl-copy` to copy guest/program collaboration links from the panel

Missing requirements are reported. Omarchy Streamer does not silently install them.

## Controls

Left-click **Stream** on the bar to open the panel. Right-click toggles Streamer Mode.

The panel exposes Streamer Mode, stream/record/replay/clip/scene controls, Collaboration, Audio Desk, Stream-Safe workspace controls, privacy status, sensitive-window warnings, and emergency buttons.

## Collaboration Core

v0.5 adds a provider-based collaboration controller. The first provider is **VDO.Ninja**, which supports browser guests, director rooms, and scene links suitable for OBS Browser Sources.

The workflow is deliberately explicit:

1. **Create Room** creates a cryptographically random room ID and password locally.
2. **Open Director** opens the password-bearing director link in the default browser.
3. **Copy Guest Invite** copies a password-bearing browser invite to the Wayland clipboard.
4. **Copy OBS Scene URL** copies a password-bearing `scene=0` group view with clean output for use as an OBS Browser Source.
5. **Rotate Room** creates fresh credentials and invalidates previously copied links.
6. **Clear Room** removes the local room credentials.

The guest link grants access to the browser collaboration room only. It does **not** grant shell access, filesystem access, Streamer IPC access, OBS WebSocket access, or access to local Streamer state.

Collaboration credentials are stored under the Streamer state directory with restrictive permissions. Normal `status` output intentionally exposes only safe metadata such as whether a room exists and whether browser/clipboard helpers are available. Room IDs, passwords, director URLs, invite URLs, and program URLs are excluded.

The plugin itself does not run a collaboration server, open a listener, change firewall rules, or proxy guest media. Media transport is handled by the selected collaboration provider.

### Collaboration actions

```text
collab.create
collab.rotate
collab.reset
collab.open-director
collab.copy-invite
collab.copy-program
```

Actions that reveal or invalidate collaboration credentials are marked confirmation-required in the action contract.

### Current collaboration boundary

v0.5 creates and manages the room workflow but does **not** claim live guest presence, guest mute/remove control, or per-guest PipeWire routing yet. Those require a live provider/device integration and will be added only when they can be verified rather than simulated.

## Emergency actions

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
omarchy-shell io.github.drecullith.streamer action collab.create ""
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
             ├── bin/obsws.py      ── localhost OBS WebSocket v5
             ├── bin/audioctl.py   ── WirePlumber/wpctl Audio Desk
             ├── bin/safetyctl.py  ── Hyprland workspace/window safety
             └── bin/collabctl.py  ── replaceable browser collaboration adapter
```

## Roadmap

### v0.6 — Live collaboration controls

- verified guest presence/status
- guest mute/remove where the active provider safely supports it
- optional one-click OBS Browser Source creation after real OBS validation
- per-guest / game / browser audio routing
- collaborator health and disconnect warnings
- provider abstraction expansion, including later Mode700 integration

### Later — Stream profiles and integrations

- Gaming / Recording / Podcast / low-spec presets
- more capture-source awareness
- configurable safety profiles
- external local integrations through the existing action contract

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, silently substitute a missing selected microphone, auto-close sensitive apps, auto-clear the clipboard, expose collaboration secrets through generic status, run a guest-facing local server, or hand external automation unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
