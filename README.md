# Omarchy Streamer

An all-in-one Streamer Mode for **Omarchy Quattro**.

Omarchy Streamer turns an Omarchy desktop into a deliberate creator/streaming workspace with OBS control, PipeWire-aware audio controls, reversible privacy protection, Stream-Safe workspace tools, managed browser guests, callback-backed guest control, production profiles, guest layouts, emergency actions, guided onboarding, and a stable local action surface for future integrations.

> Status: early **v0.9**. Core lifecycle, authenticated OBS control, Audio Desk, Stream-Safe workspace controls, managed collaboration guest slots, callback-backed guest presence/control, deterministic OBS guest layouts, production profiles, guided onboarding/preflight, emergency actions, bar UI, IPC, documentation, and CI coverage are in place. Real Omarchy/OBS/PipeWire/Hyprland and live provider-session validation are still required.

## Current v0.9

- Omarchy Quattro third-party plugin
- bar widget + popup control panel
- long-running service and explicit IPC target
- native Quattro onboarding overlay and replayable Guide
- live preflight for OBS, PipeWire, mic, privacy, Stream-Safe, and collaboration
- full [User Guide](docs/USER_GUIDE.md) and [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- reversible Streamer Mode + notification DND state
- authenticated OBS WebSocket v5 control
- stream / recording / replay-buffer / clip / scene controls
- LIVE / REC bar state from OBS
- PipeWire / WirePlumber Audio Desk with remembered microphone selection
- dedicated Stream-Safe Hyprland workspace and warning-only sensitive-window guard
- emergency **End Live + Mute** and **Stop All Capture**
- password-protected VDO.Ninja collaboration rooms
- four managed guest slots with private per-slot identities
- callback-backed guest ONLINE / OFFLINE / UNKNOWN / STALE state
- managed guest remote mic on/off and disconnect actions
- production profiles: **Gaming / Recording / Podcast / Low-spec**
- profile-controlled guest-presence refresh cadence
- managed guest OBS layouts: **auto / single / split / grid / focus:<slot>**
- profile-recommended guest layout action kept separate from profile selection
- one-click group or individual guest Browser Source creation in OBS
- room rotation and per-slot rotation to invalidate old links
- local-only collaboration/profile state with restrictive permissions
- no room password, stream ID, control ID, secret URL, or window title in generic status
- no control IDs passed on process command lines
- no root requirement, no implicit `sudo`, no automatic package installation
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

## Production profiles

Profiles are deliberately non-destructive. Selecting one never starts/stops a stream or recording and never changes streaming-service credentials.

Current profiles:

- **Gaming** — balanced live-gameplay defaults, 30-second guest refresh, auto guest layout.
- **Recording** — local-recording oriented, 30-second guest refresh, auto guest layout.
- **Podcast** — guest-focused, 15-second guest refresh, grid guest layout.
- **Low-spec** — reduced background guest polling at 60 seconds, auto guest layout.

The panel exposes previous/next profile controls. Profile selection changes Streamer preferences only.

Applying the active profile's guest layout is a separate explicit action:

```bash
omarchy-shell io.github.drecullith.streamer action profile.layout ""
```

That separation prevents a harmless profile selection from unexpectedly rearranging a live OBS scene.

## Managed guest layouts

The guest layout controller only targets OBS scene items named:

```text
Omarchy Streamer - Guest N
```

inside the dedicated collaboration scene. It does not touch gameplay, logos, alerts, webcams, or unrelated scene items.

Supported presets:

```text
auto        1 guest = single, 2 = split, 3-4 = grid
single      show only the first managed guest full canvas
split       show the first two managed guests side-by-side
grid        up to four managed guests in a 2x2 layout
focus:<N>   feature Guest N with remaining managed guests in a side rail
```

Layouts use OBS WebSocket scene-item transforms and the current OBS base canvas size rather than assuming 1920x1080. The transform path is covered by fake OBS CI tests.

Examples:

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout auto
omarchy-shell io.github.drecullith.streamer action collab.layout grid
omarchy-shell io.github.drecullith.streamer action collab.layout focus:2
```

Because layout changes are visible production changes, `collab.layout` and `profile.layout` are confirmation-marked in the public action contract.

## Guided onboarding

The first time the current onboarding version is seen, the long-running service summons the Streamer overlay once. Skip/Finish marks that tour version complete; the panel's **Guide** button reopens it without resetting state.

The seven pages cover project/safety overview, live preflight, OBS, Audio Desk, Stream-Safe/emergency controls, collaboration, and a ready-to-stream checklist.

## Controls

Left-click **Stream** on the bar to open the panel. Right-click toggles Streamer Mode.

The panel exposes Streamer Mode, production profiles, the Guide, stream/record/replay/clip/scene controls, Collaboration, managed guest slots, guest state/control, guest layouts, Audio Desk, Stream-Safe, privacy status, warnings, and emergency buttons.

## Managed guest presence and control semantics

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

The active profile controls background refresh cadence. Cached guest state becomes **STALE** after 30 seconds.

Remote mic and disconnect actions use the private control capability loaded inside the collaboration controller. Control IDs are not exposed in generic status and are not placed on process command lines.

The provider WebSocket client and callback correlation are covered by a fake local provider in CI. Real VDO.Ninja browser-session behavior still needs hardware/session validation before the project claims field verification.

## OBS collaboration provisioning

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

Browser Source provisioning is non-destructive: existing managed Browser Sources are updated/reused, but Streamer refuses to replace a source of another type that happens to use a reserved managed name.

The scene name can be overridden with `OMARCHY_STREAMER_GUEST_SCENE`.

## Collaboration security boundary

The first provider is **VDO.Ninja**. Room passwords, stream IDs, private page-control IDs, director URLs, guest URLs, and OBS source URLs remain local secrets.

Secret-bearing links leave Streamer only through explicit copy/open actions. Guest links do **not** grant shell access, filesystem access, Streamer IPC access, OBS WebSocket access, or access to local Streamer state.

The plugin does not run a collaboration server, open a listener, change firewall rules, or proxy guest media.

## Stream-Safe and emergency actions

`workspace.enter` records the current Hyprland workspace and switches to the dedicated `stream-safe` workspace. It does not move, close, hide, or kill windows. `workspace.exit` restores the recorded workspace.

`emergency.end-live` best-effort enables privacy/DND, mutes the selected mic, enters Stream-Safe, and stops the live stream.

`emergency.stop-all` performs the same sequence and also stops recording and replay buffer. One unavailable subsystem does not prevent the remaining steps from being attempted.

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
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
omarchy-shell io.github.drecullith.streamer action collab.guest-mute "1"
omarchy-shell io.github.drecullith.streamer action collab.layout focus:1
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action profile.layout ""
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

The stable action vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). UI and external integrations use the same explicit action boundary.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
BarWidget.qml
Onboarding.qml ── guided overlay
      │
Service.qml ── IPC / first-run summon / profile-aware guest refresh
      │
      └── bin/streamerctl
             ├── bin/obsws.py         ── authenticated localhost OBS WebSocket v5
             ├── bin/obsbrowser.py    ── safe Browser Source provisioning
             ├── bin/guestlayout.py   ── managed guest scene-item transforms
             ├── bin/audioctl.py      ── WirePlumber/wpctl Audio Desk
             ├── bin/safetyctl.py     ── Hyprland workspace/window safety
             ├── bin/collabctl.py     ── browser rooms + managed guest state/actions
             ├── bin/vdoapi.py        ── private page-control WebSocket + callbacks
             ├── bin/profilectl.py    ── production profile preferences
             └── bin/onboardingctl.py ── first-run completion state
```

## Roadmap

### Next — real-machine validation and audio routing

- real-session validation of callback-backed guest controls
- identify trustworthy per-guest/application PipeWire stream nodes on the actual Omarchy machine
- add per-guest audio routing only after those identities are proven stable enough
- richer guest health/quality indicators where the provider exposes trustworthy data
- camera controls only after live-session validation and UX review

### Later

- configurable/custom production profiles
- more capture-source awareness
- configurable safety profiles
- provider adapters beyond the first browser collaboration backend
- external local integrations through the existing action contract

### Hardware-validation pass

Once a real Omarchy machine is available:

- load-test service/bar/overlay QML in Quattro,
- verify first-run overlay focus and layout,
- validate real OBS/PipeWire/Hyprland behavior,
- test microphones, reconnects, sleep/wake and multi-display behavior,
- run a real multi-guest collaboration session and validate callbacks/mic/disconnect/layout behavior,
- inspect real PipeWire stream identities before implementing per-guest routing,
- capture real screenshots for the manuals.

## Why per-guest PipeWire routing is not in v0.9

WirePlumber can inspect and control individual streams, and can restore per-stream target devices. However, correctly identifying which live PipeWire stream belongs to which browser guest is environment/session-specific. v0.9 intentionally does not guess at that mapping because an incorrect guess could mute or reroute the wrong application. That feature stays behind real-machine validation.

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, expose collaboration credentials in generic status, put private guest-control IDs on process command lines, silently substitute a missing microphone, auto-close sensitive apps, clear the clipboard behind the user's back, or hand external automation unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
