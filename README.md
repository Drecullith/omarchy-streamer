# Omarchy Streamer

An all-in-one creator and streaming mode for **Omarchy Quattro**.

Omarchy Streamer coordinates OBS Studio, PipeWire/WirePlumber audio, reversible privacy protection, a dedicated Stream-Safe workspace, managed browser guests, production profiles, deterministic guest layouts, guided onboarding, validated settings, and privacy-safe diagnostics behind one explicit local action surface.

> **Version 1.0.0** — code-complete and CI-hardened. Real Omarchy/OBS/PipeWire/Hyprland hardware validation and live browser-guest field testing are still required before the project claims full field verification.

## What v1.0 includes

- Quattro bar widget, popup control panel, long-running service, and native onboarding overlay
- authenticated OBS WebSocket v5 control for streaming, recording, replay buffer, clips, and scene switching
- PipeWire/WirePlumber Audio Desk with remembered microphone selection, mute, and volume control
- reversible notification-DND privacy state
- Stream-Safe Hyprland workspace and warning-only sensitive-window detection
- emergency **End Live + Mute** and **Stop All Capture** actions
- password-protected browser collaboration rooms
- four managed guest slots with private per-slot identities
- callback-backed guest **ONLINE / OFFLINE / UNKNOWN / STALE** state
- remote managed-guest mic on/off and disconnect actions
- non-destructive OBS Browser Source provisioning
- deterministic guest layouts: `auto`, `single`, `split`, `grid`, `focus:<slot>`
- production profiles: **Gaming / Recording / Podcast / Low-spec**
- first-run guide, replayable guided tour, preflight page, user manual, and troubleshooting guide
- validated user settings with safe defaults and environment-variable overrides
- one-time non-destructive v1 state/permission migration
- redacted support snapshots designed to be safe to paste into bug reports
- stable IPC/action contract for UI, automation, and future local integrations
- no root requirement, no implicit `sudo`, no automatic package installation, and no streaming-service stream keys stored by the plugin

## Install

```bash
omarchy plugin add https://github.com/Drecullith/omarchy-streamer.git
omarchy plugin enable io.github.drecullith.streamer
```

Third-party Omarchy plugins are installed disabled first so their code can be reviewed before enabling.

### Runtime requirements

- Omarchy Quattro
- OBS Studio 28+ with obs-websocket
- Python 3
- PipeWire + WirePlumber `wpctl`
- Hyprland `hyprctl`
- `xdg-open` for browser/manual launching
- `wl-copy` for collaboration links and support-snapshot copying
- outbound HTTPS/WebSocket access to the configured browser-guest provider when collaboration is used

Missing dependencies are reported; Streamer does not silently install them.

## Production profiles

Profiles are intentionally non-destructive. Selecting one never starts/stops capture and never changes provider credentials.

| Profile | Guest refresh | Recommended guest layout |
| --- | ---: | --- |
| Gaming | 30 s | auto |
| Recording | 30 s | auto |
| Podcast | 15 s | grid |
| Low-spec | 60 s | auto |

Applying the profile's OBS layout is a separate confirmation-marked action:

```bash
omarchy-shell io.github.drecullith.streamer action profile.layout ""
```

## Validated settings

User preferences live at:

```text
~/.config/omarchy-streamer/settings.json
```

Supported v1 settings are:

```text
safeWorkspace       default: stream-safe
guestSceneName      default: Omarchy Guests
guestStateMaxAge    default: 30 seconds
guestControlTimeout default: 1.4 seconds
sensitiveDefaults   default: true
```

Use the stable action boundary instead of hand-editing JSON when possible:

```bash
omarchy-shell io.github.drecullith.streamer action settings.set 'safeWorkspace=broadcast'
omarchy-shell io.github.drecullith.streamer action settings.set 'guestStateMaxAge=45'
omarchy-shell io.github.drecullith.streamer action settings.reset 'safeWorkspace'
omarchy-shell io.github.drecullith.streamer action settings.reset ""
```

Environment overrides remain supported and take priority over file settings for recovery/testing.

## Privacy-safe support snapshot

For bug reports, prefer the sanitized snapshot over raw Streamer state:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

Or copy it to the Wayland clipboard:

```bash
omarchy-shell io.github.drecullith.streamer action support.copy ""
```

The support snapshot intentionally excludes scene names, microphone identities, window/workspace names, sensitive-window rules, collaboration URLs/credentials/IDs, OBS passwords, stream keys, and raw error text. CI includes a redaction test that seeds fake secrets and identifying names and fails if they survive the snapshot.

## State migration

v1 writes a small state-schema marker and repairs restrictive permissions on known Streamer state/config files. The migration is non-destructive: unknown user files are never deleted.

It runs automatically once when needed and can also be invoked explicitly:

```bash
omarchy-shell io.github.drecullith.streamer action state.migrate ""
```

Older collaboration-room migration remains lazy inside the collaboration controller so secret material is not duplicated into a second migration store.

## Managed guests and OBS layouts

Streamer only rearranges its own managed guest items:

```text
Omarchy Streamer - Guest N
```

inside the configured guest scene. It does not manipulate gameplay, alerts, logos, webcams, or unrelated scene items.

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout auto
omarchy-shell io.github.drecullith.streamer action collab.layout grid
omarchy-shell io.github.drecullith.streamer action collab.layout focus:2
```

A managed guest is considered **ONLINE** only when that guest page answers a correlated private-control callback. Reaching the provider server by itself is not treated as proof of guest presence.

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
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action support.snapshot ""
```

The stable action vocabulary lives in [`contracts/actions-v1.json`](contracts/actions-v1.json). High-impact actions such as stream/record changes, guest mutation, room rotation, and OBS layout changes remain confirmation-marked.

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [v1 hardware validation checklist](docs/HARDWARE_VALIDATION.md)
- [Changelog](CHANGELOG.md)
- [Security notes](SECURITY.md)

Real screenshots will be added after the first actual Quattro hardware-validation pass rather than presenting mockups as product screenshots.

## Validation boundary

The automated suite covers the action contract, settings validation, migrations, redaction, fake OBS WebSocket RPC, Browser Source provisioning, guest transforms, fake WirePlumber behavior, fake Hyprland behavior, collaboration state/secret boundaries, fake provider callbacks, production profiles, onboarding, and generic CI-machine fallback behavior.

Still waiting for the real Omarchy machine:

- actual Quattro QML rendering/focus behavior
- real OBS/PipeWire/Hyprland integration
- microphones, reconnects, sleep/wake, and multi-display behavior
- real multi-guest browser sessions and callback behavior
- stable mapping of live guest/browser audio to PipeWire nodes before any per-guest routing is implemented
- final screenshots and UX polish based on physical use

## Safety principles

Omarchy Streamer does **not** silently install packages, use root, change firewall rules, store stream keys, expose collaboration credentials in generic status, put private guest-control IDs on process command lines, silently substitute a missing microphone, auto-close sensitive apps, clear the clipboard behind the user's back, or hand external integrations unrestricted shell execution.

Every integration should be observable, reversible where practical, and explicit about missing dependencies or failed protections.

## License

MIT
