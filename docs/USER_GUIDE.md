# Omarchy Streamer User Guide

This manual covers Omarchy Streamer **v0.9**.

Omarchy Streamer is a user-level Omarchy Quattro plugin that coordinates OBS Studio, PipeWire/WirePlumber microphone controls, Streamer Privacy, Stream-Safe workspace tools, browser collaboration, callback-backed managed guest control, production profiles, guest layouts, guided onboarding, and emergency actions from one control surface.

> Hardware/session note: the control paths and automated tests are in place, but final validation still requires a real Omarchy Quattro machine with OBS, PipeWire, Hyprland, microphones, and real browser guest sessions. Real UI screenshots will be added after that pass rather than presenting mockups as product screenshots.

## 1. Install

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Runtime pieces used by the current release:

- Omarchy Quattro and `omarchy-shell`
- OBS Studio 28+ with obs-websocket
- Python 3
- PipeWire and WirePlumber `wpctl`
- Hyprland `hyprctl`
- `xdg-open` for browser/manual launching
- `wl-copy` for collaboration link copying on Wayland
- outbound WebSocket access to the collaboration provider while managed guest presence/control is active

Omarchy Streamer reports missing dependencies; it does not silently install them.

## 2. First launch and Guide

On first successful load, the native Quattro onboarding overlay appears once for the current tour version.

The seven pages cover:

1. Welcome and safety model
2. Live preflight check
3. OBS controls
4. Audio Desk
5. Stream-Safe and emergency controls
6. Collaboration
7. Ready-to-stream checklist

**Skip** and **Finish** both mark the current tour version complete. The panel's **Guide** button replays the tour later without resetting first-run state.

IPC equivalents:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
omarchy-shell io.github.drecullith.streamer action onboarding.open preflight
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

## 3. Preflight checklist

Before capture, confirm:

- OBS is installed and running.
- OBS WebSocket connects.
- PipeWire is running.
- the intended microphone is present.
- Streamer Privacy can reach Omarchy notification DND.
- Stream-Safe reports Hyprland controls available.
- Collaboration is ready if guests are needed.

A warning is not always fatal. OBS WebSocket cannot report connected while OBS itself is closed.

## 4. Bar widget

Top-level states:

- `Stream` — standby
- `STREAM` — Streamer Mode active
- `LIVE` — OBS streaming
- `REC` — OBS recording when not live

Left-click opens the control panel. Right-click toggles Streamer Mode.

## 5. Production Profiles

v0.9 adds four production profiles:

- **Gaming** — 30-second managed-guest refresh, auto guest layout
- **Recording** — 30-second refresh, auto layout
- **Podcast** — 15-second refresh, grid layout
- **Low-spec** — 60-second refresh, auto layout

Use **← Profile** / **Profile →** in the panel to cycle profiles.

Profile selection is deliberately non-destructive. It does **not**:

- start or stop streaming,
- start or stop recording,
- change stream keys/provider credentials,
- create or clear collaboration rooms,
- rearrange OBS automatically.

The selected profile changes Streamer's production preferences and managed-guest refresh cadence.

### Apply Profile Guest Layout

This is a separate button/action because changing layout is visible production state.

```bash
omarchy-shell io.github.drecullith.streamer action profile.layout ""
```

For example, Podcast recommends `grid`; Gaming/Recording/Low-spec currently recommend `auto`.

Direct profile selection is also available:

```bash
omarchy-shell io.github.drecullith.streamer action profile.apply gaming
omarchy-shell io.github.drecullith.streamer action profile.apply recording
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action profile.apply low-spec
```

## 6. Streamer Mode and Privacy

Enabling Streamer Mode attempts to enable Streamer Privacy by turning Omarchy notification DND on.

Before changing DND, Streamer records whether it was already on/off. When Privacy/Streamer Mode is disabled, it restores that previous state rather than assuming notifications should always be turned back on.

If DND cannot be confirmed, Privacy does not claim to be enabled.

Capture active + Privacy off produces a warning.

## 7. OBS control

OBS Studio 28+ includes obs-websocket. Streamer talks to OBS WebSocket v5 over localhost by default and keeps OBS authentication enabled.

Streamer does not store streaming-service stream keys.

Panel controls:

- Start/Stop Stream
- Start/Stop Recording
- Start/Stop Replay Buffer
- Save Clip
- Set Scene

**Save Clip** requires replay buffer to be running.

Scene switching uses the exact OBS scene name.

## 8. Audio Desk

Audio Desk uses WirePlumber `wpctl`.

The selected microphone is remembered by PipeWire node name rather than a temporary numeric ID, because IDs can change when devices reconnect.

Controls:

- Select/Next Mic
- Mute/Unmute Mic
- -5% volume
- +5% volume

Selecting a mic in Streamer does not silently change the desktop-wide default microphone.

If the remembered microphone disappears, Streamer reports it as missing rather than substituting another input.

## 9. Stream-Safe workspace

The default dedicated workspace is `stream-safe`.

**Enter Stream-Safe** remembers the current workspace name and switches to it. **Return Workspace** returns to the remembered workspace.

Override the name with:

```text
OMARCHY_STREAMER_SAFE_WORKSPACE
```

Stream-Safe does not move, close, hide, or kill existing windows.

## 10. Sensitive-window warnings

Streamer checks the active Hyprland window against warning rules.

Personal rules can be placed in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

Examples:

```text
class:bitwarden
title:password manager
any:my-sensitive-app
```

Matching is case-insensitive and warning-only. Titles may be inspected locally for matching but are not serialized into generic status.

## 11. Emergency controls

### End Live + Mute

Best-effort attempts:

1. Privacy/DND on
2. selected mic mute
3. enter Stream-Safe
4. stop live stream

### Stop All Capture

Performs the same sequence and also attempts to stop recording and replay buffer.

If one subsystem is unavailable, the remaining safety steps are still attempted.

## 12. Collaboration rooms

The first provider is VDO.Ninja.

Streamer generates/stores room credentials locally. It does not run a collaboration server, open a listener, proxy media, or change firewall rules.

Guest browser links do not grant access to the local shell, filesystem, Streamer IPC, OBS WebSocket, or local Streamer state.

### Create / manage room

- **Create Room** — create/reuse a password-protected room and four managed slots
- **Open Director** — open provider director page
- **Copy General Invite** — room invite without managed slot identity
- **Rotate Room** — replace room and all managed slot credentials
- **Clear Room** — remove local collaboration credentials/state

## 13. Managed guest slots

Use Guest arrows to choose Guest 1-4.

Per-slot actions:

- **Copy Guest Invite**
- **Add Guest to OBS**
- **Copy Guest OBS URL**
- **Rotate Guest Link**
- **Refresh Guests**
- **Mute Guest / Unmute Guest**
- **Disconnect Guest N**

Normal status never exposes room password, managed stream IDs, page-control IDs, or secret URLs.

## 14. Guest state semantics

**ONLINE** is strict: the managed guest page must answer a correlated private control callback.

Possible states:

- **ONLINE** — latest callback answered
- **ONLINE · STALE** — last usable state older than freshness window
- **OFFLINE** — page did not answer within callback timeout
- **CONTROL UNAVAILABLE** — provider control connection failed, so Streamer does not guess offline
- **STATUS UNKNOWN** — no usable state yet

Cached state becomes stale after 30 seconds. The active production profile controls how often background presence refresh is attempted.

Guest mic/disconnect commands also wait for their correlated callback before cached state is changed.

Private page-control IDs are loaded inside the collaboration controller from the user-only session file. They are not returned in generic status and are not placed on process command lines.

## 15. Add guests to OBS

Group source:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guests
```

Individual sources:

```text
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
...
```

The scene name can be overridden by `OMARCHY_STREAMER_GUEST_SCENE`.

Provisioning is non-destructive. If one reserved name already belongs to a non-Browser Source, Streamer refuses to overwrite it.

## 16. Guest layouts

v0.9 can arrange only the managed individual guest scene items. Unrelated OBS items are ignored.

### Auto Guest Layout

The panel's **Auto Guest Layout** resolves based on managed guest sources currently in the guest scene:

- 1 -> single
- 2 -> split
- 3-4 -> grid

### Focus Guest N

**Focus Guest N** makes the selected guest large and places the other managed guest sources in a side rail.

### Direct layout actions

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout auto
omarchy-shell io.github.drecullith.streamer action collab.layout single
omarchy-shell io.github.drecullith.streamer action collab.layout split
omarchy-shell io.github.drecullith.streamer action collab.layout grid
omarchy-shell io.github.drecullith.streamer action collab.layout focus:2
```

The layout engine queries OBS's current base canvas size and uses scene-item bounds/positions rather than assuming a fixed resolution.

`single` may disable other **managed guest** items in the collaboration scene. Applying another layout re-enables the managed items included in that layout.

## 17. Why per-guest audio routing is not here yet

WirePlumber can inspect/control individual application streams. The missing safe step is determining which local browser/audio node belongs to which specific remote guest on the target Omarchy session.

v0.9 does not guess this mapping because a wrong match could mute or reroute the wrong application.

The first real-machine collaboration test pass will inspect actual PipeWire browser/OBS topology. Per-guest routing will only be added after a stable identity strategy is demonstrated.

## 18. Common workflows

### Solo livestream

1. Choose Gaming/Recording/Low-spec as appropriate.
2. Start OBS.
3. Confirm WebSocket connected.
4. Confirm microphone.
5. Enable Streamer Mode / verify Privacy.
6. Set the intended scene.
7. Start replay buffer if clips are wanted.
8. Start Stream and confirm `LIVE`.

### Podcast / multi-guest

1. Select **Podcast** profile.
2. Create collaboration room.
3. Send managed invites.
4. Add guests to OBS.
5. Wait for expected slots to report ONLINE.
6. Use **Apply Profile Guest Layout** for the grid recommendation, or focus a selected guest.
7. Verify video/audio directly in OBS/provider director.
8. Confirm own mic + Privacy.
9. Start capture.

### Remove a guest immediately

1. Select the correct slot.
2. Confirm slot number/state.
3. Use **Disconnect Guest N**.
4. Confirm OFFLINE after callback.
5. Rotate that guest link if old access should be invalidated.

### Sensitive content appears

Use **End Live + Mute** or **Stop All Capture**.

## 19. IPC examples

```bash
omarchy-shell io.github.drecullith.streamer ping
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action profile.layout ""
omarchy-shell io.github.drecullith.streamer action stream.start ""
omarchy-shell io.github.drecullith.streamer action mic.mute ""
omarchy-shell io.github.drecullith.streamer action workspace.enter ""
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
omarchy-shell io.github.drecullith.streamer action collab.guest-mute "1"
omarchy-shell io.github.drecullith.streamer action collab.guest-disconnect "1"
omarchy-shell io.github.drecullith.streamer action collab.layout focus:1
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

The stable vocabulary lives in `contracts/actions-v1.json`.

## 20. Local state

Runtime state lives under:

```text
${XDG_STATE_HOME:-~/.local/state}/omarchy-streamer/
```

It includes reversible mode/privacy state, selected microphone identity, Stream-Safe return workspace, collaboration credentials, safe cached guest state, selected production profile, and onboarding completion.

Sensitive/local state files use user-only permissions where supported.

## 21. Safety model

Omarchy Streamer intentionally does not:

- use root or implicit `sudo`,
- install packages silently,
- change firewall rules,
- store streaming-service stream keys,
- expose collaboration secrets in generic status,
- pass private guest-control IDs on process command lines,
- claim guest presence from provider connectivity alone,
- rearrange unrelated OBS sources through guest-layout helpers,
- apply a layout merely because a profile was selected,
- guess per-guest PipeWire routing,
- silently substitute a missing microphone,
- auto-close/hide sensitive apps,
- clear the clipboard behind the user's back,
- hand external integrations unrestricted shell execution.

## 22. Validation boundary

OBS layout/profile behavior is unit-tested using fake local adapters, including filtering out unrelated scene items and transform requests.

Provider callback behavior is tested against a local fake WebSocket provider.

Those tests verify our logic/protocol handling but do not replace real Omarchy + OBS + guest-session testing.

## 23. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
