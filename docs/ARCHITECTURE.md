# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming, recording, audio, privacy, collaboration, guest control, production profiles, guest layouts, and onboarding without hidden privileged actions or permanent ownership of user settings.

The v0.9 architecture has twelve main pieces:

1. `BarWidget.qml` — user-facing status and controls, including profiles, managed guest state/control, layout helpers, and Guide access.
2. `Onboarding.qml` — native Quattro overlay for first-run guidance, preflight, and replayable help.
3. `Service.qml` — long-running Quickshell service, IPC boundary, one-time first-run summon, and profile-aware guest-presence refresh loop.
4. `bin/streamerctl` — action router, reversible mode/privacy state, emergency actions, onboarding summon path, profiles, layouts, and collaboration boundary.
5. `bin/obsws.py` — authenticated localhost OBS WebSocket v5 adapter.
6. `bin/obsbrowser.py` — non-destructive OBS Browser Source provisioning.
7. `bin/guestlayout.py` — deterministic layout transforms for managed guest scene items only.
8. `bin/audioctl.py` / `bin/safetyctl.py` — WirePlumber audio and Hyprland stream-safety adapters.
9. `bin/collabctl.py` — browser rooms, managed guest identities, safe guest-state cache, provider-control orchestration, and OBS collaboration source orchestration.
10. `bin/vdoapi.py` — minimal private page-control WebSocket client with correlated callbacks and explicit timeouts.
11. `bin/profilectl.py` — user-only production-profile preferences and guest refresh/layout recommendations.
12. `bin/onboardingctl.py` — user-only onboarding completion state.

## Core invariants

- No root requirement or implicit `sudo`.
- No package-manager invocation.
- Missing dependencies are reported rather than installed.
- State changed by Streamer Mode should be restorable.
- UI and external integrations call the same explicit action contract.
- Stream keys and streaming-service credentials are not stored.
- Sensitive-window detection is warning-only.
- Stream-Safe never auto-moves, closes, hides, or kills user windows.
- Window titles are not exposed in status output.
- Emergency actions continue best-effort when one subsystem is unavailable.
- Collaboration room passwords, managed stream IDs, page-control IDs, and secret URLs are never included in generic status or IPC snapshots.
- Private page-control IDs are not passed as process command-line arguments.
- Secret-bearing collaboration actions, remote guest mutations, and visible OBS layout changes are explicit and confirmation-marked.
- A provider WebSocket connection alone never counts as guest presence.
- Managed OBS Browser Sources never overwrite a non-Browser Source with the same reserved name.
- Guest layout helpers only touch reserved `Omarchy Streamer - Guest N` scene items.
- Selecting a production profile never starts/stops capture and never changes provider credentials.
- Applying a profile's layout is a separate action from selecting the profile.
- Onboarding and profile status contain no stream/collaboration credentials.

## Plugin lifecycle

The manifest declares:

```text
service
bar-widget
overlay
```

The service is the long-running coordinator. The bar widget reads safe status and invokes explicit actions. `Onboarding.qml` uses Omarchy's normal overlay summon lifecycle.

On service startup, onboarding state is checked and the first-run guide is summoned once when eligible. While a collaboration room with managed slots is active, the service runs callback-backed guest refresh on a cadence supplied by the selected production profile.

The bar/status path itself does not perform provider network I/O; it reads the local guest-state cache.

## Runtime state

General state lives under:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Persisted state includes reversible Streamer Mode/privacy state, Audio Desk mic selection, previous Stream-Safe workspace, collaboration session credentials, cached safe guest state, selected production profile, and onboarding completion.

Sensitive state files are written with user-only permissions where supported. OBS output state remains authoritative in OBS and is queried live.

## Production profiles

`profilectl.py` exposes four initial profiles:

```text
gaming
recording
podcast
low-spec
```

Each profile contains safe production preferences only:

```text
label
guestRefreshSeconds
guestLayout
privacyRecommended
description
```

The current v0.9 profile values are:

```text
gaming    refresh 30s  layout auto
recording refresh 30s  layout auto
podcast   refresh 15s  layout grid
low-spec  refresh 60s  layout auto
```

Profile selection is state-only. It does not start OBS, stream, record, create guests, switch scenes, or mutate collaboration credentials.

`Service.qml` consumes `guestRefreshSeconds` to tune its managed guest presence timer. `profile.layout` separately resolves the active profile's `guestLayout` and applies it through `guestlayout.py`.

The profile state file is written with user-only permissions where supported.

## Managed guest layout engine

`guestlayout.py` connects to OBS through the existing authenticated `obsws.py` adapter.

It enumerates the configured collaboration scene and selects only items whose names match:

```text
Omarchy Streamer - Guest N
```

Unrelated scene items are ignored.

Supported layouts:

```text
auto
single
split
grid
focus:<slot>
```

`auto` resolves by managed source count: 1 -> single, 2 -> split, 3-4 -> grid.

The controller queries OBS `GetVideoSettings` so layout geometry is derived from the current base canvas size. It then uses `SetSceneItemEnabled` and `SetSceneItemTransform` with bounded scale-inner boxes.

`single` may disable other managed guest items in the collaboration scene. `focus:<slot>` keeps the focused guest large and places the remaining managed guests in a side rail. Other production sources are never targeted.

Visible layout changes are confirmation-marked through `collab.layout` and `profile.layout`.

## IPC and action mediation

The Quickshell service registers:

```text
io.github.drecullith.streamer
```

Primary calls:

```text
ping
status
refresh
action <action-name> <optional-arg>
enable
disable
toggle
```

Profile actions:

```text
profile.apply <gaming|recording|podcast|low-spec>
profile.next
profile.previous
profile.layout
```

Guest layout action:

```text
collab.layout <auto|single|split|grid|focus:N>
```

The action vocabulary is defined in `contracts/actions-v1.json`.

## OBS integration

`obsws.py` speaks OBS WebSocket v5 using Python's standard library, keeps authentication enabled, defaults to localhost, and stores no stream-service credentials.

`obsbrowser.py` provisions managed Browser Sources. `guestlayout.py` subsequently arranges their scene items without changing Browser Source URLs or provider credentials.

The default collaboration scene is `Omarchy Guests`, overridable through `OMARCHY_STREAMER_GUEST_SCENE`.

Reserved source names are `Omarchy Streamer - Guests` and `Omarchy Streamer - Guest N`. If a reserved name already exists as a non-`browser_source`, provisioning fails safely rather than replacing it.

## Collaboration identity and provider control

A collaboration session has a room ID/password plus four managed guest slots by default. Each slot has a safe slot number/label and private `streamId` / `controlId` capabilities.

A managed guest invite can carry the private page-control capability, while the solo OBS URL receives only the view identity. OBS therefore does not receive the guest page's control capability.

`vdoapi.py` opens the provider control channel, joins the private control ID, sends one action with a unique callback ID, ignores unrelated messages, accepts only the matching callback, and times out instead of assuming success.

Private control IDs are loaded from the user-only collaboration session file and passed to the imported provider adapter in memory rather than on the CLI.

## Guest presence model

A slot is **ONLINE** only when its managed page answers a correlated `getDetails` callback. Merely opening the provider API WebSocket does not prove page presence.

Safe cached state contains:

```text
slot
online
micEnabled
checkedAt
stale
error
```

The cache is stored with user-only permissions where supported. `stale` becomes true after 30 seconds by default.

Four slot probes run concurrently, while cache writes are serialized/atomic so one guest update cannot clobber another.

Remote mic and disconnect actions update cached state only after a matching command callback. Timeouts and connection failures surface as errors rather than success.

These paths are protocol-tested in CI against a local fake WebSocket provider. Real provider/browser-session behavior remains a field-validation item.

## Audio integration and routing boundary

`audioctl.py` uses WirePlumber `wpctl`. It remembers a microphone by PipeWire node name and resolves the current numeric ID on demand. Missing selected devices are surfaced rather than silently replaced.

Per-guest PipeWire routing is intentionally not implemented in v0.9. WirePlumber can inspect and control individual streams, but assigning a browser/application audio node to a specific remote guest requires observing real provider/browser audio topology on the target system. Streamer will not guess at that identity because a wrong match could mute or reroute the wrong application.

The real-machine validation pass must establish a stable mapping strategy before routing actions are added.

## Stream-Safe and emergency actions

`safetyctl.py` uses explicit Hyprland workspace/window queries and dispatch. Sensitive-window rules are warning-only and titles are not serialized into status.

`emergency.end-live` independently attempts Privacy/DND on, selected microphone mute, Stream-Safe workspace entry, and OBS stream stop.

`emergency.stop-all` additionally attempts recording and replay-buffer stop.

## Health model

`streamerctl status` returns version 9 state containing safe aggregate state from OBS, Audio Desk, Stream-Safe, Collaboration, guest-state cache, Onboarding, and Production Profiles.

Unknown/unreachable subsystems are represented explicitly rather than being presented as healthy.

## Tests

CI validates:

- manifest/action contract and v0.9 version,
- shell/Python syntax,
- safe status behavior without desktop services,
- fake OBS WebSocket RPC,
- OBS Browser Source create/update/collision behavior,
- managed guest layout filtering and transforms,
- grid/focus/single behavior without touching unrelated scene items,
- production profile default/apply/cycle behavior and state permissions,
- profile status secret-field guard,
- fake WirePlumber/wpctl behavior,
- fake Hyprland workspace/window behavior,
- sensitive-window title non-disclosure,
- Stream-Safe enter/restore,
- collaboration state permissions/migration/slot rotation,
- collaboration secret non-disclosure,
- parallel four-slot guest refresh without cache clobbering,
- callback-backed mic/disconnect state transitions,
- provider WebSocket callback correlation against a fake provider,
- onboarding state/lifecycle/manual hooks,
- public documentation remaining integration-neutral.

The remaining validation class is real Omarchy Quattro + OBS + PipeWire + Hyprland + browser collaboration testing, including real scene transforms, guest sessions, visual layout review, and discovery of safe per-guest audio-node identity.
