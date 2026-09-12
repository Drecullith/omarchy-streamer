# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace with OBS control, PipeWire-aware audio controls, reversible privacy protection, Stream-Safe workspace tools, managed browser guests, callback-backed guest control, emergency actions, guided onboarding, and a stable local action surface for future integrations.

> Status: early **v0.8**. Core lifecycle, authenticated OBS control, Audio Desk, Stream-Safe workspace controls, managed collaboration guest slots, one-click OBS Browser Source provisioning, callback-backed guest presence/control, guided onboarding/preflight, emergency actions, bar UI, IPC, documentation, and CI coverage are in place. Real Omarchy/OBS/PipeWire/Hyprland and live provider-session validation are still required.

## Current v0.8

- Omarchy Quattro third-party plugin
- bar widget + popup control panel
- long-running service and explicit IPC target
- native Quattro onboarding overlay
- automatic one-time first-run walkthrough
- replayable **Guide** from the Streamer panel
- live preflight page for OBS, PipeWire, mic, privacy, Stream-Safe, and collaboration
- full [User Guide](docs/USER_GUIDE.md)
- symptom-based [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- reversible Streamer Mode + notification DND state
- authenticated OBS WebSocket v5 control
- stream / recording / replay-buffer / clip / scene controls
- LIVE / REC bar state from OBS
- PipeWire / WirePlumber Audio Desk
- remembered microphone selection without changing the desktop default
- mic mute/unmute/toggle and volume controls
- missing-microphone warnings
- dedicated named **Stream-Safe** Hyprland workspace
- warning-only sensitive-window guard
- emergency **End Live + Mute** and **Stop All Capture**
- password-protected VDO.Ninja collaboration rooms
- four managed guest slots with private per-slot identities
- callback-backed guest ONLINE / OFFLINE / UNKNOWN / STALE state
- managed guest remote mic on/off and disconnect actions
- 15-second guest presence refresh while a collaboration room is active
- per-slot invite and solo OBS URLs
- one-click group or individual guest Browser Source creation in OBS
- room rotation and per-slot rotation to invalidate old links
- local-only collaboration credential and guest-state storage with restrictive permissions
- no room password, stream ID, control ID, secret URL, or window title in generic status
- no control IDs passed on process command lines
- no root requirement
- no implicit `sudo`
- no automatic package installation
- no streaming-service stream keys stored by the plugin

## Install on Omarchy Quattro

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

### Runtime requirements

- Omarchy Quattro
- OBS Studio 28+ with obs-websocket
- Python 3
- PipeWire + WirePlumber `wpctl`
- Hyprland `hyprctl`
- `xdg-open` for browser/manual launching
- `wl-copy` for collaboration link copying
- outbound HTTPS/WebSocket access to the configured collaboration provider when using browser guests

Missing requirements are reported. Omarchy Streamer does not silently install them.

## Guided onboarding

The first time the current onboarding version is seen, the long-running service summons the Streamer overlay once.

The seven pages cover:

1. project/safety overview,
2. live preflight checks,
3. OBS control,
4. Audio Desk,
5. Stream-Safe + emergency controls,
6. collaboration,
7. ready-to-stream checklist.

**Skip** and **Finish** both mark the current tour version complete so it does not reopen every login. The main Streamer panel has a **Guide** button for replaying the tour without resetting first-run state.

IPC equivalents:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
omarchy-shell io.github.drecullith.streamer action onboarding.open preflight
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

Onboarding completion state contains no stream/collaboration credentials and is stored with user-only permissions where possible.

## Controls

Left-click **Stream** on the bar to open the panel. Right-click toggles Streamer Mode.

The panel exposes Streamer Mode, the replayable Guide, stream/record/replay/clip/scene controls, Collaboration, managed guest slots, callback-backed guest state/control, Audio Desk, Stream-Safe workspace controls, privacy status, warnings, and emergency buttons.

## Managed guest workflow

Each of the four managed guest slots has a human-facing slot number plus private VDO.Ninja stream/control identities. Those private IDs are deliberately excluded from normal Streamer status and IPC snapshots.

A typical workflow:

1. **Create Room**.
2. Select Guest 1-4.
3. **Copy Guest Invite** and send it privately.
4. **Add Guest to OBS** to create/update that guest in the dedicated `Omarchy Guests` scene.
5. When the guest page answers its private control callback, the panel can show it as **ONLINE**.
6. Use **Mute Guest / Unmute Guest** or **Disconnect Guest** when needed.
7. **Rotate Guest Link** to invalidate one slot, or **Rotate Room** to replace all room/slot credentials.

### Guest presence and control semantics

Streamer does not treat a successful connection to the provider API server as proof that a guest is online.

For each managed slot, Streamer connects to the provider's documented private page-control channel and sends `getDetails` with a unique callback ID. The slot is considered online only if that guest page returns the correlated callback.

Guest state is cached locally and contains only safe metadata:

```text
slot
online
micEnabled
checkedAt
stale
error
```

It never contains the room password, managed stream ID, or private page-control ID.

The long-running service refreshes managed guest presence every 15 seconds while a collaboration room is active. Cached state becomes **STALE** after 30 seconds.

Remote microphone commands also wait for the correlated callback before updating the cached mic state. Disconnect uses the managed guest page's private control capability and only marks the slot offline after its command callback.

The WebSocket client and callback correlation are covered by a fake local provider in CI. Real VDO.Ninja browser-session behavior still needs the hardware/session validation pass before this project claims field verification.

### OBS provisioning rules

Group source:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guests
```

Individual source:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guest N
```

Browser Source provisioning is deliberately non-destructive: existing managed Browser Sources are updated/reused, but Streamer refuses to replace a source of another type that happens to use a reserved managed name.

The scene name can be overridden with `OMARCHY_STREAMER_GUEST_SCENE`.

## Collaboration security boundary

The first provider is **VDO.Ninja**. Room passwords, stream IDs, private page-control IDs, director URLs, guest URLs, and OBS source URLs remain local secrets.

Secret-bearing links leave Streamer only through explicit copy/open actions. Guest links do **not** grant shell access, filesystem access, Streamer IPC access, OBS WebSocket access, or access to local Streamer state.

Private page-control IDs are loaded from the user-only session file directly inside the collaboration controller and passed to the provider adapter in memory. They are not exposed in generic status and are not supplied as process command-line arguments.

The plugin does not run a collaboration server, open a listener, change firewall rules, or proxy guest media.

## Stream-Safe and emergency actions

`workspace.enter` records the current Hyprland workspace by name and switches to the dedicated `stream-safe` named workspace. It does not move, close, hide, or kill windows. `workspace.exit` restores the recorded workspace.

Sensitive-window checks are warning-only. Window titles may be inspected locally for matching but are not serialized into status.

`emergency.end-live` best-effort enables privacy/DND, mutes the selected mic, enters Stream-Safe, and stops the live stream.

`emergency.stop-all` performs the same sequence and also stops recording and replay buffer. One unavailable subsystem does not prevent the remaining emergency steps from being attempted.

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
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
omarchy-shell io.github.drecullith.streamer action collab.guest-mute "1"
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

The stable action vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). UI and external integrations use the same explicit action boundary.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
BarWidget.qml
Onboarding.qml ── guided overlay
      │
Service.qml ── IPC / first-run summon / guest presence refresh
      │
      └── bin/streamerctl
             ├── bin/obsws.py         ── authenticated localhost OBS WebSocket v5
             ├── bin/obsbrowser.py    ── safe Browser Source provisioning
             ├── bin/audioctl.py      ── WirePlumber/wpctl Audio Desk
             ├── bin/safetyctl.py     ── Hyprland workspace/window safety
             ├── bin/collabctl.py     ── browser rooms + managed guest state/actions
             ├── bin/vdoapi.py        ── private page-control WebSocket + callbacks
             └── bin/onboardingctl.py ── first-run completion state
```

## Roadmap

### Next — deeper collaboration/audio

- real-session validation of callback-backed guest controls
- per-guest PipeWire routing
- guest-source layout helpers
- richer guest health/quality indicators where the provider exposes trustworthy data
- camera controls only after live-session validation and UX review

### Later — Stream profiles and integrations

- Gaming / Recording / Podcast / low-spec presets
- more capture-source awareness
- configurable safety profiles
- provider adapters beyond the first browser collaboration backend
- external local integrations through the existing action contract

### Hardware-validation pass

Once a real Omarchy machine is available:

- load-test the service/bar/overlay QML in Quattro,
- verify first-run overlay focus and layout,
- validate real OBS/PipeWire/Hyprland behavior,
- test microphones, reconnects, sleep/wake and multi-display behavior,
- run a real multi-guest collaboration session and validate page-control callbacks/mic/disconnect behavior,
- capture real screenshots for the user/troubleshooting manuals.

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, expose collaboration credentials in generic status, put private guest-control IDs on process command lines, silently substitute a missing microphone, auto-close sensitive apps, clear the clipboard behind the user's back, or hand external automation unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT