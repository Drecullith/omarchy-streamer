# Omarchy Streamer Troubleshooting

This guide covers common **v0.9** symptoms. Start with Streamer's own status before changing system configuration.

```bash
bash ~/.config/omarchy/plugins/io.github.drecullith.streamer/bin/streamerctl status | python3 -m json.tool
```

If your plugin directory differs, run `bin/streamerctl status` from the installed plugin root.

## Stream widget missing

```bash
omarchy plugin enable io.github.drecullith.streamer
```

If the shell was already running during an unusual install/update state, reload/restart the Omarchy shell using the normal Omarchy workflow.

## First-run guide did not appear

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
python3 bin/onboardingctl.py status | python3 -m json.tool
```

To deliberately re-enable first-run eligibility:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

The automatic first-run summon is attempted once per shell session.

## Production profile looks wrong

Inspect profile state:

```bash
python3 bin/profilectl.py status | python3 -m json.tool
```

Select explicitly if needed:

```bash
omarchy-shell io.github.drecullith.streamer action profile.apply gaming
omarchy-shell io.github.drecullith.streamer action profile.apply recording
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action profile.apply low-spec
```

Profile selection does not start/stop capture and does not automatically rearrange OBS.

## Guest refresh cadence did not change with profile

The current intended values are:

```text
Gaming    30s
Recording 30s
Podcast   15s
Low-spec  60s
```

Confirm `profiles.guestRefreshSeconds` in:

```bash
bash bin/streamerctl status | python3 -m json.tool
```

The long-running service consumes that value for the managed guest refresh timer. The change affects future timer firings; it does not force a network refresh every time you click a profile.

## Apply Profile Guest Layout fails

First confirm:

- OBS is running,
- OBS WebSocket is connected,
- managed individual guest Browser Sources have been added to the `Omarchy Guests` scene.

Then inspect the active profile:

```bash
python3 bin/profilectl.py status | python3 -m json.tool
```

`profile.layout` simply resolves that profile's recommended layout and passes it to the guest layout controller.

## Auto Guest Layout says no managed guest sources exist

The layout engine does not create guest sources. Add guests to OBS first.

Expected managed names:

```text
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
Omarchy Streamer - Guest 3
Omarchy Streamer - Guest 4
```

The group source `Omarchy Streamer - Guests` is not used by the individual layout engine.

## Focus Guest N fails

`focus:N` requires `Omarchy Streamer - Guest N` to exist as a scene item in the configured collaboration scene.

Try:

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout focus:1
```

If Guest 1 was never added to the scene, add it first with **Add Guest to OBS**.

## Layout changed only guest sources, not my gameplay/logo/alerts

That is intentional. v0.9's layout engine filters by the reserved `Omarchy Streamer - Guest N` naming pattern and ignores unrelated scene items.

If an unrelated source is ever moved/disabled by a guest-layout action, treat that as a bug.

## Single layout hid other guests

That is intentional. `single` shows only the first managed guest and disables other managed guest scene items.

Apply `auto`, `split`, `grid`, or an appropriate `focus:N` layout to bring managed guest items back into the active layout.

## Layout geometry looks wrong

Streamer queries OBS `GetVideoSettings` and uses the current base canvas dimensions.

If the live result still looks wrong:

1. verify OBS base canvas settings,
2. confirm the managed sources are standard Browser Sources created by Streamer,
3. try `auto` or `grid`,
4. inspect the scene directly in OBS before going live.

The transform path is unit-tested, but visual composition still needs the real-machine validation pass.

## OBS says missing

```bash
command -v obs
```

Streamer does not install OBS automatically.

## OBS running but WebSocket unavailable

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

Keep OBS WebSocket authentication enabled. Streamer normally reads OBS's local WebSocket config and connects to localhost. The default port is 4455 unless OBS is configured differently.

## OBS authentication error

Streamer uses OBS's configured WebSocket password. If OBS configuration changed while running, reload/restart the relevant app state and retry.

The password is not stored in the repository or Streamer's normal state directory.

## Start Stream fails

Verify the streaming output works directly in OBS first. Streamer asks OBS to start the already-configured stream; it does not create provider credentials or stream keys.

## Save Clip fails

Replay buffer must be running. Start it first and verify OBS replay-buffer settings if that fails.

## Scene switching fails

Use the exact OBS scene name.

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

## PipeWire not detected

```bash
pgrep -x pipewire
command -v wpctl
```

Audio Desk requires WirePlumber `wpctl`.

## No microphone appears / selected mic says MISSING

```bash
python3 bin/audioctl.py status | python3 -m json.tool
```

Reconnect the device if needed, then deliberately select an available mic. Streamer will not silently substitute another input.

## Mic mute/volume controls fail

```bash
command -v wpctl
python3 bin/audioctl.py status | python3 -m json.tool
```

Confirm the selected source is still present.

## Why can't I route each remote guest separately yet?

That is intentionally withheld in v0.9.

WirePlumber can inspect/control individual streams, but Streamer has not yet proven a stable mapping between a specific remote browser guest and a specific local PipeWire stream node on the actual Omarchy machine.

Guessing could mute or reroute the wrong application. The first hardware collaboration session will inspect the real PipeWire topology before any per-guest routing feature is enabled.

## Privacy will not turn on

```bash
omarchy-shell notifications dndState
```

Expected output is `on` or `off`. If it is unknown/unavailable, Streamer deliberately does not claim Privacy is active.

## Privacy changed my notification setting

Streamer records the previous DND state and restores it when Privacy/Streamer Mode is disabled.

Do not delete state files while Streamer Mode is active unless you understand the restoration consequence.

## Stream-Safe unavailable

```bash
command -v hyprctl
hyprctl activeworkspace -j
python3 bin/safetyctl.py status | python3 -m json.tool
```

## Stream-Safe did not move windows

Intentional. It switches workspace but does not auto-move/hide/close/kill windows.

## Sensitive-window warning

Advisory only. Personal rules live in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

## `wl-copy` missing

Needed only for copying collaboration links through the panel:

```bash
command -v wl-copy
```

## Open Director unavailable

```bash
command -v xdg-open
```

## Guest invite stopped working after rotation

Expected. **Rotate Guest Link** invalidates that slot's old identities; **Rotate Room** replaces all room/slot credentials.

Send the newly copied invite.

## Add Guest to OBS fails

Confirm OBS WebSocket is connected.

Streamer reserves:

```text
Omarchy Streamer - Guests
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
Omarchy Streamer - Guest 3
Omarchy Streamer - Guest 4
```

If a reserved name already belongs to a non-Browser Source, Streamer refuses to replace it.

## Guest shows STATUS UNKNOWN

No usable callback-backed state exists yet.

```bash
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
python3 bin/collabctl.py status | python3 -m json.tool
```

UNKNOWN is preferable to inventing online/offline state.

## Guest shows CONTROL UNAVAILABLE

The provider control connection itself failed. This is not treated as OFFLINE because Streamer could not reach the control path well enough to ask the guest page.

Check network/DNS/TLS and refresh again. Do not rotate room credentials merely because the provider endpoint is temporarily unreachable.

## Guest shows OFFLINE but appears joined

OFFLINE means the managed guest page did not answer `getDetails` within the timeout.

Check:

- current (not rotated) invite was used,
- correct managed slot,
- guest page still open,
- browser did not suspend/kill the page,
- network path healthy.

Then refresh.

## Guest says ONLINE · STALE

Last callback-backed state is older than the freshness window (30s by default). Refresh guests. If refresh keeps failing, state should move toward OFFLINE/CONTROL UNAVAILABLE rather than appearing fresh forever.

## Mute/Unmute Guest fails

Remote mic control only succeeds after the managed page returns the correlated command callback.

Verify selected guest ONLINE, refresh once, retry, and use the provider Director as fallback if immediate manual intervention is needed.

Streamer does not change displayed remote mic state merely because a WebSocket send succeeded.

## Disconnect Guest fails

Streamer marks the slot OFFLINE only after the page acknowledges disconnect.

If it times out/fails, use **Open Director** for immediate provider-side management and rotate the guest link afterward if old access should be invalidated.

## Guest state wrong after rotation

Rotation clears cached state for the replaced identity. New state starts UNKNOWN until the new managed page answers.

The cache is:

```text
~/.local/state/omarchy-streamer/collab-guest-state.json
```

Do not publish the whole state directory; the neighboring collaboration session file contains private capabilities.

## Generic status exposes collaboration secrets

Treat that as a security bug.

Normal status must not contain room/password, `streamId`, `controlId`, or secret invite/director/source URLs. CI checks this boundary.

## Emergency button reports partial success

Emergency actions are best-effort. Verify OBS directly if the OBS connection itself was unavailable.

## Diagnostic commands

General:

```bash
bash bin/streamerctl doctor | python3 -m json.tool
```

OBS:

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

Profiles:

```bash
python3 bin/profilectl.py status | python3 -m json.tool
```

Audio:

```bash
python3 bin/audioctl.py status | python3 -m json.tool
```

Stream-Safe:

```bash
python3 bin/safetyctl.py status | python3 -m json.tool
```

Collaboration:

```bash
python3 bin/collabctl.py status | python3 -m json.tool
```

Force guest refresh:

```bash
python3 bin/collabctl.py action collab.guest-refresh | python3 -m json.tool
```

Onboarding:

```bash
python3 bin/onboardingctl.py status | python3 -m json.tool
```

## Before reporting a bug

Include:

- Omarchy Streamer version
- Omarchy/Quattro revision if known
- whether OBS is running
- whether PipeWire/WirePlumber are running
- selected production profile
- failing action name
- sanitized status/error output

Do **not** post collaboration invite URLs, room passwords, managed stream/control IDs, OBS WebSocket passwords, stream keys, or other credentials in public bug reports.
