# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that coordinates streaming, recording, audio, privacy, collaboration, guest control, production profiles, guest layouts, onboarding, validated settings, migrations, and diagnostics without hidden privileged actions or permanent ownership of unrelated user state.

## v1 components

1. `BarWidget.qml` — user-facing status and controls.
2. `Onboarding.qml` — native Quattro first-run/replayable guide and preflight overlay.
3. `Service.qml` — long-running Quickshell service, IPC boundary, first-run summon, and profile-aware guest refresh loop.
4. `bin/streamerctl` — canonical action router and aggregate status boundary.
5. `bin/obsws.py` — authenticated localhost OBS WebSocket v5 adapter.
6. `bin/obsbrowser.py` — non-destructive managed OBS Browser Source provisioning.
7. `bin/guestlayout.py` — deterministic transforms for managed guest scene items only.
8. `bin/audioctl.py` — WirePlumber/wpctl Audio Desk.
9. `bin/safetyctl.py` — Hyprland Stream-Safe workspace and sensitive-window warning adapter.
10. `bin/collabctl.py` — rooms, managed guest identities, safe guest-state cache, provider orchestration, and OBS source orchestration.
11. `bin/vdoapi.py` — private page-control WebSocket client with correlated callbacks/timeouts.
12. `bin/profilectl.py` — production-profile preferences and refresh/layout recommendations.
13. `bin/onboardingctl.py` — onboarding completion state.
14. `bin/settings.py` — validated non-secret settings model.
15. `bin/withsettings.py` — injects resolved validated settings into adapter subprocesses without rewriting their command interfaces.
16. `bin/migrate.py` — one-time non-destructive state schema/permission migration.
17. `bin/diagnostics.py` — privacy-safe support snapshot builder.

## Core invariants

- No root requirement or implicit `sudo`.
- No package-manager invocation.
- Missing dependencies are reported rather than installed.
- Stream keys and streaming-service credentials are not stored.
- UI and external integrations use the same explicit action contract.
- Streamer Mode/Privacy state should be reversible where practical.
- Sensitive-window detection is warning-only.
- Stream-Safe never auto-moves/closes/hides/kills user windows.
- Window titles are not exposed in generic status.
- Emergency actions continue best-effort if one subsystem is unavailable.
- Collaboration room passwords, managed stream IDs, private page-control IDs, and secret URLs are excluded from generic collaboration status.
- Private guest-control IDs are not placed on process command lines.
- Provider connectivity alone never proves guest presence.
- Managed OBS Browser Sources never overwrite a non-Browser Source with the same reserved name.
- Guest-layout helpers target only reserved `Omarchy Streamer - Guest N` items.
- Selecting a production profile never starts/stops capture and never changes provider credentials.
- Profile selection and visible OBS layout application remain separate actions.
- Unknown settings are rejected rather than silently accepted.
- v1 migration never deletes unknown user files.
- Support snapshots intentionally exclude identifying production names and secrets.

## Plugin lifecycle

The manifest declares:

```text
service
bar-widget
overlay
```

`Service.qml` continuously reads aggregate status from `streamerctl`, exposes IPC at `io.github.drecullith.streamer`, summons onboarding once when eligible, and runs managed guest refresh at the cadence supplied by the active profile.

The bar/status path reads cached guest state; it does not perform provider network I/O on every UI refresh.

## Canonical action boundary

The stable action vocabulary lives in `contracts/actions-v1.json`.

Primary IPC shape:

```text
ping
status
refresh
action <action-name> <optional-arg>
enable
disable
toggle
```

Examples added for v1:

```text
settings.set key=value
settings.reset [key]
state.migrate
support.snapshot
support.copy
```

High-impact actions such as stream/record mutation, room rotation, guest mutation, and OBS layout changes remain confirmation-marked. Read-only support snapshot generation is not.

## Validated settings model

`settings.py` owns one schema-versioned non-secret settings file:

```text
$XDG_CONFIG_HOME/omarchy-streamer/settings.json
```

Supported v1 values:

```text
safeWorkspace
guestSceneName
guestStateMaxAge
guestControlTimeout
sensitiveDefaults
```

Each field has strict type/range/name validation. File settings are written atomically with user-only permissions where supported.

Environment variables remain supported as highest-priority overrides for recovery/testing. `withsettings.py` resolves settings once and exports the existing `OMARCHY_STREAMER_*` variables to child adapters, allowing legacy adapter interfaces to remain stable while the user-facing configuration model becomes centralized.

`safetyctl.py` also resolves the validated settings directly so Stream-Safe behavior remains correct when it is queried on its own.

## v1 migration model

`migrate.py` writes:

```text
$XDG_STATE_HOME/omarchy-streamer/state-schema.json
```

with schema version 1.

On first v1 use, `streamerctl` runs migration when the marker is absent. The migration:

- creates Streamer state/config directories if needed,
- repairs known directory permissions to user-only,
- repairs known Streamer state/config files to user-only,
- writes the state-schema marker atomically,
- never deletes unknown files,
- refuses to migrate over a state schema newer than the current build.

Older collaboration-session structure still migrates lazily inside `collabctl.py`, avoiding duplication of room secrets into a second migration store.

## Support snapshot / redaction boundary

`diagnostics.py` receives normal aggregate status and emits only a deliberately reduced support schema.

Included data is limited to useful booleans/counts/version/profile/settings-source information, such as dependency availability, capture booleans, guest-state counts, and active profile ID.

Explicitly excluded:

```text
OBS scene names
microphone/device identities
window/workspace names
sensitive-window rule strings
room IDs/passwords
streamId/controlId values
invite/director/source URLs
OBS WebSocket passwords
stream keys
raw error strings
```

CI seeds fake values for these categories and fails if any survive the support snapshot.

## Runtime state

State root:

```text
$XDG_STATE_HOME/omarchy-streamer/
```

or `~/.local/state/omarchy-streamer/`.

Persisted state includes reversible mode/privacy state, selected mic identity, Stream-Safe return workspace, collaboration session credentials, safe guest cache, selected profile, onboarding completion, and the state-schema marker.

User configuration root:

```text
$XDG_CONFIG_HOME/omarchy-streamer/
```

or `~/.config/omarchy-streamer/`.

It contains validated settings and optional sensitive-window warning rules.

## Production profiles

Initial profiles:

```text
gaming    refresh 30s  layout auto
recording refresh 30s  layout auto
podcast   refresh 15s  layout grid
low-spec  refresh 60s  layout auto
```

Profile selection is state-only. `Service.qml` consumes `guestRefreshSeconds`; `profile.layout` separately resolves and applies `guestLayout` through `guestlayout.py`.

## Managed guest layout engine

`guestlayout.py` connects through the authenticated OBS adapter and only targets scene items matching:

```text
Omarchy Streamer - Guest N
```

Supported layouts:

```text
auto
single
split
grid
focus:<slot>
```

Geometry is based on OBS `GetVideoSettings`, not a hard-coded canvas size. Visible layout changes are confirmation-marked.

## Collaboration identity and guest presence

A collaboration session contains room credentials plus four managed slots. Each managed slot has a safe slot number/label and private `streamId`/`controlId` capabilities.

The solo OBS URL receives view identity only; OBS does not receive the guest page-control capability.

`vdoapi.py` joins the private control ID, sends one action with a unique callback ID, ignores unrelated messages, accepts only the correlated callback, and times out instead of assuming success.

A slot is **ONLINE** only after its managed page answers a correlated `getDetails` callback. Safe cache fields are limited to:

```text
slot
online
micEnabled
checkedAt
stale
error
```

Remote mic/disconnect cached state changes only after command acknowledgement.

## Audio boundary

`audioctl.py` remembers the selected microphone by PipeWire node name and resolves current numeric IDs on demand. Missing selected devices are surfaced instead of silently replaced.

Per-guest PipeWire routing is intentionally not implemented in v1. The missing safety prerequisite is a proven mapping between a specific remote guest and a specific live local PipeWire/browser audio node on the target Omarchy machine. Streamer will not guess that identity.

## Health/status versions

`streamerctl status` is currently **status version 10** and aggregates OBS, audio, safety, collaboration, onboarding, profiles, and validated settings.

Unknown/unreachable subsystems remain explicit instead of being presented as healthy.

## CI / release invariants

CI validates:

- exact `1.0.0` manifest identity,
- JSON/shell/Python syntax,
- unique action IDs,
- required confirmation classes,
- Service IPC acceptance for v1 actions,
- validated settings defaults/ranges/atomic permissions/environment precedence/reset behavior,
- one-time migration and non-destructive unknown-file preservation,
- support-snapshot redaction against seeded fake secrets/names,
- safe behavior on a generic CI machine,
- fake OBS WebSocket RPC,
- Browser Source create/update/collision behavior,
- guest layout transforms/filtering,
- profile apply/cycle behavior,
- fake WirePlumber/wpctl behavior,
- fake Hyprland workspace/window behavior,
- collaboration permission/migration/secret boundaries,
- parallel guest refresh and callback-backed mic/disconnect transitions,
- fake provider WebSocket callback correlation,
- onboarding state/lifecycle/manual hooks,
- public documentation remaining integration-neutral.

The remaining validation class is physical Omarchy Quattro + OBS + PipeWire + Hyprland + real browser collaboration testing.
