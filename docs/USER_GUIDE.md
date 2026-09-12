# Omarchy Streamer User Guide

This manual covers **Omarchy Streamer v1.0.0**.

Omarchy Streamer is a user-level Omarchy Quattro plugin that coordinates OBS, PipeWire/WirePlumber microphone controls, reversible privacy, Stream-Safe workspace tools, browser collaboration, callback-backed guest control, production profiles, guest layouts, guided onboarding, validated settings, and privacy-safe diagnostics.

> Real UI screenshots will be added after the first physical Omarchy validation pass. The project does not present mockups as if they were tested product screenshots.

## 1. Install

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Runtime requirements:

- Omarchy Quattro and `omarchy-shell`
- OBS Studio 28+ with obs-websocket
- Python 3
- PipeWire and WirePlumber `wpctl`
- Hyprland `hyprctl`
- `xdg-open`
- `wl-copy`
- outbound HTTPS/WebSocket access when browser collaboration is used

Missing dependencies are reported. Streamer does not silently install them.

## 2. First launch and Guide

The first successful load summons the native guided overlay once for the current onboarding version. The Guide covers preflight, OBS, Audio Desk, Stream-Safe/emergency actions, Collaboration, Production Profiles, and a ready-to-stream checklist.

**Skip** and **Finish** suppress repeat first-run prompts. Use the panel's **Guide** button to replay it later.

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
omarchy-shell io.github.drecullith.streamer action onboarding.open preflight
```

## 3. Bar widget and top-level state

- `Stream` — standby
- `STREAM` — Streamer Mode active
- `LIVE` — OBS streaming
- `REC` — OBS recording when not live

Left-click opens the panel. Right-click toggles Streamer Mode.

## 4. Production Profiles

Profiles change Streamer preferences without starting/stopping capture or touching provider credentials.

- **Gaming** — 30-second guest refresh, `auto` guest layout
- **Recording** — 30-second guest refresh, `auto` layout
- **Podcast** — 15-second guest refresh, `grid` layout
- **Low-spec** — 60-second guest refresh, `auto` layout

Use the profile arrows in the panel or:

```bash
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
```

Applying the profile's OBS guest layout is deliberately separate:

```bash
omarchy-shell io.github.drecullith.streamer action profile.layout ""
```

That prevents a harmless profile selection from unexpectedly rearranging a live scene.

## 5. Streamer Mode and Privacy

Enabling Streamer Mode attempts to enable Omarchy notification DND. Streamer records the previous DND state and restores it when Privacy/Streamer Mode is disabled.

If DND cannot be confirmed, Privacy does not claim to be enabled. Capture active + Privacy off raises a warning.

## 6. OBS controls

Streamer uses authenticated OBS WebSocket v5 on localhost and does not store streaming-service stream keys.

Panel controls include:

- Start/Stop Stream
- Start/Stop Recording
- Start/Stop Replay Buffer
- Save Clip
- Set Scene

`Save Clip` requires the replay buffer to be running. Scene switching uses the exact OBS scene name.

## 7. Audio Desk

Audio Desk uses WirePlumber `wpctl`.

The selected microphone is remembered by PipeWire node name rather than a temporary numeric ID. Controls include mic selection/cycling, mute/unmute, and volume changes.

Streamer does not silently replace the desktop-wide default microphone. If the selected device disappears, Streamer warns instead of substituting another input.

## 8. Stream-Safe and sensitive-window warnings

The default dedicated workspace is `stream-safe`.

**Enter Stream-Safe** remembers the current workspace and switches to the dedicated workspace. **Return Workspace** restores the remembered workspace.

Sensitive-window rules are warning-only. Streamer does not move, hide, close, or kill applications. Window titles may be checked locally but are not serialized into generic Streamer status.

Personal rules live in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

Examples:

```text
class:bitwarden
title:password manager
any:my-sensitive-app
```

## 9. Emergency controls

**End Live + Mute** best-effort attempts:

1. Privacy/DND on
2. selected mic mute
3. enter Stream-Safe
4. stop live stream

**Stop All Capture** also attempts to stop recording and replay buffer.

One unavailable subsystem does not prevent the remaining emergency steps from being attempted.

## 10. Collaboration rooms

The first browser provider is VDO.Ninja.

Streamer generates/stores room credentials locally. It does not run a collaboration server, open a listener, proxy media, or change firewall rules.

A guest link does not grant shell, filesystem, Streamer IPC, OBS WebSocket, or local-state access.

Room controls include Create Room, Open Director, Copy General Invite, Rotate Room, and Clear Room.

## 11. Managed guest slots

There are four managed Guest slots. Per-slot actions include:

- Copy Guest Invite
- Add Guest to OBS
- Copy Guest OBS URL
- Rotate Guest Link
- Refresh Guests
- Mute/Unmute Guest
- Disconnect Guest

Normal status never exposes room passwords, managed stream IDs, page-control IDs, or secret URLs.

### What ONLINE means

A guest is **ONLINE** only when that managed guest page answers a correlated private-control callback. Reaching the provider server alone does not count.

Possible states:

- **ONLINE** — current callback answered
- **ONLINE · STALE** — last usable state is older than the freshness window
- **OFFLINE** — page did not answer before callback timeout
- **CONTROL UNAVAILABLE** — provider-control connection failed, so Streamer does not guess offline
- **STATUS UNKNOWN** — no usable state yet

Guest mic/disconnect commands also wait for correlated callbacks before cached state changes.

## 12. OBS guest provisioning and layouts

Default managed scene/source names:

```text
Scene:  Omarchy Guests
Source: Omarchy Streamer - Guests
Source: Omarchy Streamer - Guest N
```

Provisioning is non-destructive. If a reserved managed name belongs to a different OBS source type, Streamer refuses to overwrite it.

Guest layouts touch only `Omarchy Streamer - Guest N` items:

```text
auto
single
split
grid
focus:<N>
```

Examples:

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout auto
omarchy-shell io.github.drecullith.streamer action collab.layout focus:2
```

The layout engine queries the current OBS base canvas instead of assuming 1920x1080.

## 13. Validated settings

v1 introduces one validated non-secret settings model at:

```text
~/.config/omarchy-streamer/settings.json
```

Supported values:

| Setting | Default | Validation |
| --- | --- | --- |
| `safeWorkspace` | `stream-safe` | 1-64 safe name characters |
| `guestSceneName` | `Omarchy Guests` | 1-80 printable characters |
| `guestStateMaxAge` | `30` | 10-600 seconds |
| `guestControlTimeout` | `1.4` | 0.25-15 seconds |
| `sensitiveDefaults` | `true` | boolean |

Prefer the action interface:

```bash
omarchy-shell io.github.drecullith.streamer action settings.set 'safeWorkspace=broadcast'
omarchy-shell io.github.drecullith.streamer action settings.set 'guestSceneName=Creator Guests'
omarchy-shell io.github.drecullith.streamer action settings.set 'guestStateMaxAge=45'
omarchy-shell io.github.drecullith.streamer action settings.reset 'safeWorkspace'
omarchy-shell io.github.drecullith.streamer action settings.reset ""
```

Invalid/unknown settings fail instead of being silently accepted.

Environment overrides remain available and take priority over file values:

```text
OMARCHY_STREAMER_SAFE_WORKSPACE
OMARCHY_STREAMER_GUEST_SCENE
OMARCHY_STREAMER_GUEST_STATE_MAX_AGE
OMARCHY_STREAMER_VDO_API_TIMEOUT
OMARCHY_STREAMER_SENSITIVE_DEFAULTS
```

## 14. v1 state migration

On first v1 use, Streamer creates a small state-schema marker and repairs restrictive permissions on known Streamer files/directories.

The migration is non-destructive: unknown user files are not deleted.

Manual invocation:

```bash
omarchy-shell io.github.drecullith.streamer action state.migrate ""
```

Older collaboration-room structure is still migrated lazily by the collaboration controller so secret values are not duplicated into a second migration store.

## 15. Privacy-safe support snapshot

For bug reports, use the sanitized support snapshot instead of pasting raw state:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

Copy it to the clipboard:

```bash
omarchy-shell io.github.drecullith.streamer action support.copy ""
```

The support snapshot excludes:

- OBS scene names
- microphone identities/device names
- window/workspace names
- sensitive-window rule text
- room passwords and room IDs
- managed stream/control IDs
- invite/director/source URLs
- OBS WebSocket passwords
- streaming-service stream keys
- raw error text

It keeps only safe booleans/counts/version/profile/settings-source information useful for debugging. CI explicitly seeds fake secrets/names and fails if they survive redaction.

## 16. Common workflows

### Solo livestream

1. Pick a profile.
2. Start OBS.
3. Confirm OBS WebSocket connected.
4. Confirm the intended microphone.
5. Enable Streamer Mode and verify Privacy.
6. Set the intended scene.
7. Start replay buffer if clips are wanted.
8. Start Stream and confirm `LIVE`.

### Podcast / multi-guest

1. Select Podcast profile.
2. Create collaboration room.
3. Send managed guest invites privately.
4. Add guests to OBS.
5. Wait for expected slots to report ONLINE.
6. Apply the profile guest layout or focus a guest.
7. Verify real guest video/audio in OBS/provider director.
8. Confirm your mic + Privacy.
9. Start capture.

### Sensitive content appears

Use **End Live + Mute** or **Stop All Capture**.

## 17. IPC examples

```bash
omarchy-shell io.github.drecullith.streamer ping
omarchy-shell io.github.drecullith.streamer status
omarchy-shell io.github.drecullith.streamer action stream.start ""
omarchy-shell io.github.drecullith.streamer action mic.mute ""
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action support.snapshot ""
```

The stable vocabulary lives in `contracts/actions-v1.json`.

## 18. Local state and safety model

Runtime state lives under:

```text
${XDG_STATE_HOME:-~/.local/state}/omarchy-streamer/
```

User configuration lives under:

```text
${XDG_CONFIG_HOME:-~/.config}/omarchy-streamer/
```

Omarchy Streamer intentionally does not use root, silently install packages, change firewall rules, store stream keys, expose collaboration secrets in generic status, put private guest-control IDs on process command lines, claim guest presence from provider connectivity alone, rearrange unrelated OBS sources, guess per-guest PipeWire routing, silently substitute a missing mic, auto-close sensitive apps, or hand integrations unrestricted shell execution.

## 19. Validation boundary

CI covers settings, migrations, support redaction, the public action contract, fake OBS WebSocket RPC, Browser Source provisioning, guest scene transforms, fake WirePlumber behavior, fake Hyprland behavior, collaboration secret boundaries, fake provider callbacks, profiles, onboarding, and fallback behavior.

Still waiting for the physical Omarchy machine: real QML rendering/focus, actual OBS/PipeWire/Hyprland behavior, microphones/reconnects/sleep/wake/multi-display, real multi-guest browser sessions, and trustworthy per-guest audio-node identification.

## 20. Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
