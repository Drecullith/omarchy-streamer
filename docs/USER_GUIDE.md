# Omarchy Streamer User Guide

This manual covers Omarchy Streamer v0.7.

Omarchy Streamer is a user-level Omarchy Quattro plugin that coordinates OBS Studio, PipeWire/WirePlumber microphone controls, Streamer Privacy, Stream-Safe workspace tools, browser collaboration, and emergency actions from one control surface.

> Hardware note: the control paths and automated tests are in place, but the project still requires final real-machine validation on Omarchy Quattro with OBS, PipeWire, Hyprland, microphones and guest sessions. Real UI screenshots will be added after that validation so the manual does not present mockups as actual product screenshots.

## 1. Install

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled so their code can be reviewed before enabling.

Runtime pieces used by the current release:

- Omarchy Quattro and `omarchy-shell`
- OBS Studio 28+ with obs-websocket
- Python 3
- PipeWire and WirePlumber `wpctl`
- Hyprland `hyprctl`
- `xdg-open` for opening the browser collaboration director/manual
- `wl-copy` for copying collaboration links on Wayland

Omarchy Streamer does not silently install missing dependencies.

## 2. First launch

On the first successful plugin load, Omarchy Streamer checks its local onboarding state. If the current tour version has not been completed, the native Quattro onboarding overlay opens once.

The tour has seven pages:

1. Welcome and safety model
2. Live preflight check
3. OBS controls
4. Audio Desk
5. Stream-Safe and emergency controls
6. Collaboration
7. Ready-to-stream checklist

**Skip** marks the current tour complete so it does not reappear every login. **Finish** also marks it complete. Replaying the guide later does not erase settings or force first-run state again.

The guide can also be summoned through IPC:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

To deliberately make the first-run tour eligible again:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

## 3. Preflight checklist

Before a live stream, confirm the following:

- OBS Studio is installed and running.
- OBS WebSocket connects successfully.
- PipeWire is running.
- The intended microphone is present.
- Streamer Privacy can reach Omarchy notification DND.
- Stream-Safe reports Hyprland controls available.
- If guests are needed, Collaboration reports ready.

The onboarding preflight page reads the same local status model as the main plugin. It does not expose stream keys, collaboration room passwords, managed guest IDs, or window titles.

A warning is not always fatal. For example, OBS WebSocket cannot report connected while OBS itself is closed.

## 4. Bar widget

The bar widget shows the current top-level state:

- `Stream` — standby
- `STREAM` — Streamer Mode active
- `LIVE` — OBS is currently streaming
- `REC` — OBS is recording when not live

Left-click opens the Streamer control panel. Right-click toggles Streamer Mode.

The panel is the normal place to control capture, audio, privacy, Stream-Safe and collaboration.

## 5. Streamer Mode and privacy

Streamer Mode is the plugin's reversible session state. Enabling it attempts to enable Streamer Privacy by turning Omarchy notification DND on.

Before changing DND, the plugin records whether DND was already on or off. When Streamer Mode/Privacy is disabled, it restores that previous state rather than assuming notifications should always be turned back on.

If Omarchy notification DND cannot be reached, Privacy does not claim to be enabled.

When capture is active and Privacy is off, the panel raises a warning.

## 6. OBS setup

OBS Studio 28+ includes obs-websocket. Omarchy Streamer talks to the OBS WebSocket v5 API over localhost by default.

The plugin reads OBS's own local WebSocket configuration for the port/password. It does not store streaming-service stream keys.

Keep OBS WebSocket authentication enabled.

If OBS is installed but closed, use **Launch OBS**. After OBS starts, Streamer will begin reporting its WebSocket state.

### OBS controls

The panel supports:

- Start Stream / Stop Stream
- Start Recording / Stop Recording
- Start Replay Buffer / Stop Replay Buffer
- Save Clip
- Set Scene

The current OBS program scene is displayed when available.

### Replay-buffer clips

**Save Clip** requires the OBS replay buffer to be active. If the replay buffer cannot start, check the corresponding OBS output settings first.

### Scene switching

Enter the exact OBS scene name and choose **Set Scene**. Streamer asks OBS to switch the current program scene; it does not silently create normal production scenes.

## 7. Audio Desk

Audio Desk uses WirePlumber's `wpctl` interface.

The selected microphone is remembered by its PipeWire node name rather than by a temporary numeric object ID. That matters because PipeWire IDs can change when devices reconnect.

Controls:

- Select/Next Mic
- Mute Mic / Unmute Mic
- -5% volume
- +5% volume

Selecting a microphone in Streamer does not silently replace the desktop-wide default microphone.

If a remembered microphone disappears, Streamer reports it as missing. It does not quietly switch to another input.

Before going live, verify the microphone name, mute state and volume shown in Audio Desk.

## 8. Stream-Safe workspace

Streamer can use a dedicated named Hyprland workspace, `stream-safe` by default.

**Enter Stream-Safe** records the current workspace name and switches to the dedicated workspace.

**Return Workspace** returns to the recorded workspace.

The workspace name can be overridden with:

```text
OMARCHY_STREAMER_SAFE_WORKSPACE
```

Stream-Safe deliberately does not move, close, hide or kill existing windows.

## 9. Sensitive-window warnings

Streamer checks the active Hyprland window against warning rules.

Default rules cover common password/authenticator-style applications. Users can add personal warning rules in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

Rule formats:

```text
class:bitwarden
title:password manager
any:my-sensitive-app
```

Matching is case-insensitive and warning-only.

A window title may be inspected locally for matching, but the title itself is not serialized into generic Streamer status.

## 10. Emergency controls

### End Live + Mute

This is a best-effort sequence that attempts to:

1. enable Streamer Privacy/DND,
2. mute the selected microphone,
3. enter Stream-Safe,
4. stop the live stream.

### Stop All Capture

This attempts the same safety sequence and also stops:

- recording,
- replay buffer.

Emergency actions are deliberately best-effort. If one subsystem is unavailable, the remaining safety steps are still attempted.

These buttons are intended for mistakes, unexpected sensitive content, audio problems, or any moment when ending capture quickly matters more than preserving the current production state.

## 11. Collaboration overview

The current collaboration provider is VDO.Ninja.

Omarchy Streamer creates and stores the room credentials locally. The plugin itself does not run a collaboration server, open a listener, proxy media, or change firewall rules.

A guest browser link does not grant access to:

- the local shell,
- the filesystem,
- Streamer IPC,
- OBS WebSocket,
- local Streamer state.

### Create a room

Choose **Create Room**. The plugin generates a random password-protected room and managed guest slots.

**Open Director** opens the provider's director page in the default browser.

### General guest invite

**Copy General Invite** copies a password-bearing room invite. Use this when individual managed slot identity is unnecessary.

### Managed guest slots

v0.7 includes four managed guest slots.

Use the Guest arrows to choose Guest 1-4, then:

- **Copy Guest Invite** — copy that slot's private guest link
- **Add Guest to OBS** — create/update that slot's Browser Source
- **Copy Guest OBS URL** — copy its clean solo source URL
- **Rotate Guest Link** — invalidate only that slot's previous private identities

Normal Streamer status never exposes the room password, managed stream IDs, page-control IDs or secret URLs.

### Group guests in OBS

**Add Group to OBS** creates or updates:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guests
```

Individual slots use:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guest N
```

The scene name can be overridden with:

```text
OMARCHY_STREAMER_GUEST_SCENE
```

Streamer manages only its own reserved source names. If one of those names already belongs to a different OBS source type, Streamer refuses to overwrite it.

### Rotate Room

**Rotate Room** replaces the room and managed guest credentials. Previously shared room and slot links stop representing the current Streamer session.

### Clear Room

**Clear Room** deletes the locally stored collaboration session credentials.

## 12. Common workflows

### Solo livestream

1. Start OBS.
2. Open the Streamer panel.
3. Confirm OBS WebSocket connected.
4. Confirm the correct microphone in Audio Desk.
5. Enable Streamer Mode and verify Privacy.
6. Enter Stream-Safe if desired.
7. Select the intended OBS scene.
8. Start the replay buffer if clips are wanted.
9. Start Stream.
10. Confirm the bar shows LIVE.

### Record without streaming

1. Confirm the microphone and scene.
2. Enable Streamer Mode/Privacy if notifications should be suppressed.
3. Start Recording.
4. Confirm the bar shows REC when not live.
5. Stop Recording when finished.

### Stream with guests

1. Create a collaboration room.
2. Select a managed Guest slot.
3. Copy that Guest invite and send it privately.
4. Add that Guest to OBS.
5. Repeat for each additional guest.
6. Open Director for provider-side guest management.
7. Verify the `Omarchy Guests` scene/source layout in OBS.
8. Confirm your own microphone and Privacy.
9. Start capture only after the guest feed is visually/audio checked.

### Something sensitive appears

Use **End Live + Mute** if only the livestream must end, or **Stop All Capture** if all OBS capture should stop.

## 13. Status and IPC

Streamer exposes:

```text
io.github.drecullith.streamer
```

Useful examples:

```bash
omarchy-shell io.github.drecullith.streamer ping
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer action stream.start ""
omarchy-shell io.github.drecullith.streamer action mic.mute ""
omarchy-shell io.github.drecullith.streamer action workspace.enter ""
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

The stable action vocabulary is documented in `contracts/actions-v1.json`.

## 14. Local state

Runtime state lives under:

```text
${XDG_STATE_HOME:-~/.local/state}/omarchy-streamer/
```

This includes reversible mode/privacy state, selected microphone identity, Stream-Safe return workspace, collaboration credentials, and onboarding completion.

Files containing collaboration or onboarding state are created with restrictive user-only permissions where possible.

User warning-rule configuration lives separately under:

```text
~/.config/omarchy-streamer/
```

## 15. Safety model

Omarchy Streamer intentionally does not:

- use root or implicit `sudo`,
- install packages silently,
- change firewall rules,
- store streaming-service stream keys,
- expose collaboration secrets in generic status,
- silently substitute a missing selected microphone,
- auto-close or auto-hide sensitive applications,
- clear the clipboard behind the user's back,
- hand external integrations unrestricted shell execution.

The project favors explicit actions, visible warnings, reversible state, and fail-closed behavior for protections that cannot be confirmed.

## 16. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for symptom-based fixes and diagnostic commands.
