# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace with OBS control, PipeWire-aware audio controls, reversible privacy protection, stream-safe workspace tools, managed browser guests, emergency actions, and a stable local action surface for future integrations.

> Status: early **v0.6**. Core lifecycle, authenticated OBS control, Audio Desk, Stream-Safe workspace controls, managed collaboration guest slots, one-click OBS Browser Source provisioning, sensitive-window warnings, emergency actions, bar UI, IPC, and CI coverage are in place. Real Omarchy/OBS/PipeWire/Hyprland hardware validation is still required.

## Current v0.6

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
- warning-only sensitive-window guard
- emergency **End Live + Mute** and **Stop All Capture**
- provider-based browser collaboration core
- password-protected VDO.Ninja room workflow
- four managed guest slots with stable per-slot stream identities
- private per-slot page-control IDs reserved for later verified remote guest control
- per-slot invite and solo OBS URLs
- one-click group or individual guest Browser Source creation in OBS
- room rotation and per-slot rotation to invalidate old links
- local-only collaboration credential storage with restrictive permissions
- no room password, stream ID, control ID, or secret URL in generic status/IPC snapshots
- no root requirement
- no implicit `sudo`
- no automatic package installation
- no stream keys stored by the plugin
- CI coverage for manifest, contracts, OBS RPC, OBS Browser Source provisioning, Audio Desk, Stream-Safe, and collaboration behavior

## Install on Omarchy Quattro

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

### Runtime requirements

- Omarchy Quattro
- OBS Studio 28+ with obs-websocket
- Python 3 for the local controllers
- PipeWire + WirePlumber `wpctl` for Audio Desk
- Hyprland `hyprctl` for Stream-Safe workspace/window checks
- `xdg-open` to launch a browser collaboration director
- `wl-copy` to copy guest/source links from the panel

Missing requirements are reported. Omarchy Streamer does not silently install them.

## Controls

Left-click **Stream** on the bar to open the panel. Right-click toggles Streamer Mode.

The panel exposes Streamer Mode, stream/record/replay/clip/scene controls, Collaboration, managed guest slots, Audio Desk, Stream-Safe workspace controls, privacy status, sensitive-window warnings, and emergency buttons.

## Managed guest workflow

v0.6 extends the collaboration core with four managed guest slots.

Each slot has three pieces of private local state:

- a human-facing slot number/label,
- a stable VDO.Ninja stream ID used by that guest's publish/view links,
- a private VDO.Ninja page-control ID reserved for later verified guest control.

The private IDs are intentionally excluded from normal Streamer status and IPC snapshots.

A typical workflow is:

1. **Create Room**.
2. Select Guest 1–4 in the Streamer panel.
3. **Copy Guest Invite** and send it to that collaborator.
4. **Add Guest to OBS** to create/update that guest's Browser Source inside the dedicated `Omarchy Guests` scene.
5. Repeat for additional guests.
6. Use **Rotate Guest Link** if only one collaborator's link/control capability should be invalidated.
7. Use **Rotate Room** to invalidate every room and slot link at once.

A generic room invite and group-scene source remain available when individual slot identity is unnecessary.

### OBS provisioning rules

`collab.obs-add-program` creates or updates:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guests
```

`collab.obs-add-slot <N>` creates or updates:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guest N
```

The source is an OBS `browser_source` configured with the provider URL at 1920×1080.

Provisioning is deliberately non-destructive:

- the dedicated scene is created if missing,
- an existing managed Browser Source is updated instead of duplicated,
- an existing managed source can be added to the dedicated scene if it is not already present,
- if the intended source name already belongs to a non-Browser Source, Streamer refuses instead of replacing it.

The scene name can be overridden with:

```text
OMARCHY_STREAMER_GUEST_SCENE
```

## Collaboration security boundary

The first collaboration provider is **VDO.Ninja**. Room passwords, stream IDs, private page-control IDs, director URLs, guest URLs, and OBS source URLs remain local secrets.

Secret-bearing links only leave Streamer through explicit copy/open actions. Guest links grant access to the browser collaboration room only; they do **not** grant shell access, filesystem access, Streamer IPC access, OBS WebSocket access, or local Streamer state access.

The plugin does not run a collaboration server, open a listener, change firewall rules, or proxy guest media.

### Current live-control boundary

v0.6 gives every managed guest a stable stream identity and a private page-control capability so later guest presence/mute/remove controls have a trustworthy target.

Streamer still does **not** claim live guest presence, remote mute/remove state, or per-guest PipeWire routing yet. Those will be added only after the provider control path is tested against a real session instead of being simulated.

## Stream-Safe workspace

`workspace.enter` records the current Hyprland workspace by name and switches to the dedicated `stream-safe` named workspace. It does not move, close, hide, or kill windows. `workspace.exit` restores the recorded workspace.

Sensitive-window checks are warning-only. Window titles may be used locally for matching but are not serialized into status.

## Emergency actions

`emergency.end-live` best-effort enables privacy/DND, mutes the selected mic, enters Stream-Safe, and stops the live stream.

`emergency.stop-all` performs the same safety sequence and also stops recording and the replay buffer.

One unavailable subsystem does not prevent the remaining emergency steps from being attempted.

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
omarchy-shell io.github.drecullith.streamer action collab.copy-slot-invite "1"
omarchy-shell io.github.drecullith.streamer action collab.obs-add-slot "1"
```

The stable action vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). The UI and external integrations use the same explicit action boundary.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
BarWidget.qml
      │
Service.qml ── IPC
      │
      └── bin/streamerctl
             ├── bin/obsws.py      ── authenticated localhost OBS WebSocket v5
             ├── bin/obsbrowser.py ── safe Browser Source provisioning
             ├── bin/audioctl.py   ── WirePlumber/wpctl Audio Desk
             ├── bin/safetyctl.py  ── Hyprland workspace/window safety
             └── bin/collabctl.py  ── browser rooms + managed guest slots
```

## Roadmap

### v0.7 — User guide and guided onboarding

- full user guide/manual
- first-run setup walkthrough
- contextual popups/tooltips explaining each section
- replayable guided tour from the panel
- setup/preflight checklist for OBS, mic, privacy, Stream-Safe, and collaboration
- troubleshooting guide with screenshots

### After onboarding — verified live guest control

- provider-verified guest presence
- individual guest mute/remove controls
- per-guest health/state
- per-guest PipeWire routing
- guest-source layout helpers

### Later — Stream profiles and integrations

- Gaming / Recording / Podcast / low-spec presets
- more capture-source awareness
- configurable safety profiles
- provider adapters beyond the first browser collaboration backend
- external local integrations through the existing action contract

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, expose collaboration credentials in generic status, silently substitute a missing selected microphone, auto-close sensitive apps, clear the clipboard, or hand external automation unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
