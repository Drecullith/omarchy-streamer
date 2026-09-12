# Omarchy Streamer Troubleshooting

This guide covers **v1.0.0**. Start with Streamer's own safe status before changing system configuration.

```bash
bash bin/streamerctl status | python3 -m json.tool
```

For anything you plan to paste into a bug report, use the **sanitized support snapshot** instead:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

## Stream widget missing

```bash
omarchy plugin enable io.github.drecullith.streamer
```

If the shell was already running during an unusual install/update state, reload/restart Omarchy shell using its normal workflow.

## First-run guide did not appear

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

To deliberately re-enable first-run eligibility:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

## Settings say invalid / Settings Ready is false

Inspect the validated model:

```bash
python3 bin/settings.py status | python3 -m json.tool
```

The settings file is:

```text
~/.config/omarchy-streamer/settings.json
```

Unknown keys, invalid workspace names, unsafe numeric ranges, and unsupported schema versions fail closed instead of being silently ignored.

Reset one value:

```bash
omarchy-shell io.github.drecullith.streamer action settings.reset 'safeWorkspace'
```

Reset all file settings:

```bash
omarchy-shell io.github.drecullith.streamer action settings.reset ""
```

Environment overrides take priority over file values. If a setting appears to ignore the file, check the matching `OMARCHY_STREAMER_*` environment variable.

## Changing settings had no effect

Use Streamer's normal action/status path rather than launching internal controllers directly. `streamerctl` injects validated resolved settings into the collaboration/layout adapters.

Check:

```bash
bash bin/streamerctl status | python3 -m json.tool
```

Then retry the action through:

```bash
omarchy-shell io.github.drecullith.streamer action ...
```

## v1 state migration did not run

The automatic migration runs when the v1 state-schema marker is absent.

Manual run:

```bash
omarchy-shell io.github.drecullith.streamer action state.migrate ""
```

The marker is stored under the Streamer state directory as `state-schema.json`. Migration repairs permissions on known files but does not delete unknown user files.

If migration reports a state schema newer than this build, stop and update Streamer rather than forcing an older migration over newer state.

## Support snapshot copy fails

`support.copy` requires `wl-copy`:

```bash
command -v wl-copy
```

You can still print the snapshot without clipboard support:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

The snapshot intentionally omits scene names, mic identities, window/workspace names, rule text, URLs, collaboration credentials/IDs, OBS passwords, stream keys, and raw error strings.

If any of those appear, treat it as a security/privacy bug.

## Production profile looks wrong

```bash
python3 bin/profilectl.py status | python3 -m json.tool
```

Select explicitly:

```bash
omarchy-shell io.github.drecullith.streamer action profile.apply gaming
omarchy-shell io.github.drecullith.streamer action profile.apply recording
omarchy-shell io.github.drecullith.streamer action profile.apply podcast
omarchy-shell io.github.drecullith.streamer action profile.apply low-spec
```

Profile selection never starts/stops capture or automatically rearranges OBS.

## Guest refresh cadence did not change

Expected defaults:

```text
Gaming    30s
Recording 30s
Podcast   15s
Low-spec  60s
```

Confirm `profiles.guestRefreshSeconds` in Streamer status. The service uses that value for future guest-refresh timer firings.

## Apply Profile Guest Layout / Guest Layout fails

Confirm OBS is running, WebSocket is connected, and individual managed guest Browser Sources already exist in the configured guest scene.

Managed names are:

```text
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
Omarchy Streamer - Guest 3
Omarchy Streamer - Guest 4
```

The layout engine does not create guest sources and does not rearrange unrelated gameplay, alerts, logos, or webcams.

Try:

```bash
omarchy-shell io.github.drecullith.streamer action collab.layout auto
omarchy-shell io.github.drecullith.streamer action collab.layout grid
omarchy-shell io.github.drecullith.streamer action collab.layout focus:1
```

`single` intentionally disables other **managed guest** items; another layout re-enables managed items included in that layout.

## OBS missing / WebSocket unavailable

```bash
command -v obs
python3 bin/obsws.py status | python3 -m json.tool
```

Keep OBS WebSocket authentication enabled. Streamer reads OBS's local WebSocket configuration and does not store streaming-service stream keys.

## Start Stream fails

Verify the configured stream works directly in OBS first. Streamer only asks OBS to start the already-configured output.

## Save Clip fails

The replay buffer must be running. Check OBS replay-buffer settings if it will not start.

## Scene switching fails

Use the exact OBS scene name.

## PipeWire not detected / mic missing

```bash
pgrep -x pipewire
command -v wpctl
python3 bin/audioctl.py status | python3 -m json.tool
```

Streamer will not silently substitute another microphone if the remembered source disappears.

## Why can't I route each remote guest separately yet?

This remains deliberately withheld until real hardware/session validation.

WirePlumber can inspect/control individual streams, but Streamer has not yet proven a stable mapping between a specific remote guest and a specific local PipeWire node on the target machine. Guessing could mute/reroute the wrong application.

## Privacy will not turn on

```bash
omarchy-shell notifications dndState
```

Expected result is `on` or `off`. If it is unknown/unreachable, Streamer deliberately does not claim Privacy is active.

## Stream-Safe unavailable

```bash
command -v hyprctl
hyprctl activeworkspace -j
bash bin/streamerctl status | python3 -m json.tool
```

If you customized `safeWorkspace`, confirm the validated settings status rather than editing internal controller constants.

Stream-Safe does not auto-move/hide/close/kill windows.

## Sensitive-window warning

Advisory only. Personal rules live in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

## Collaboration says `wl-copy` or `xdg-open` missing

```bash
command -v wl-copy
command -v xdg-open
```

Streamer reports missing helpers instead of installing them.

## Guest invite stopped after rotation

Expected. **Rotate Guest Link** invalidates that slot's old identities. **Rotate Room** replaces all room/slot credentials.

## Add Guest to OBS fails

Confirm OBS WebSocket connected. If a reserved Streamer name already belongs to a non-Browser Source, Streamer refuses to overwrite it.

## Guest states

### STATUS UNKNOWN

No usable callback-backed state exists yet. Refresh:

```bash
omarchy-shell io.github.drecullith.streamer action collab.guest-refresh ""
```

### CONTROL UNAVAILABLE

The provider-control connection failed. Streamer does not guess OFFLINE when it cannot reach the control path.

### OFFLINE but guest appears joined

The managed guest page did not answer the correlated callback before timeout. Check the current invite/slot, that the page is still open, browser suspension, and network health.

### ONLINE · STALE

The last usable callback is older than `guestStateMaxAge` (30 seconds by default). Refresh guests. You can change the validated freshness window with:

```bash
omarchy-shell io.github.drecullith.streamer action settings.set 'guestStateMaxAge=45'
```

### Remote mute/unmute fails

The displayed mic state changes only after a correlated callback confirms the command. Use the provider Director as fallback if immediate intervention is needed.

### Disconnect fails

Streamer marks the guest OFFLINE only after command acknowledgement. Use **Open Director** if immediate provider-side removal is needed, then rotate the guest link if old access should be invalidated.

## Generic status exposes collaboration secrets

Treat this as a security bug. Generic collaboration status must not expose room/password, `streamId`, `controlId`, or secret invite/director/source URLs.

For public reports use `streamerctl support`, not a dump of the whole state directory.

## Emergency button reports partial success

Emergency actions are best-effort. Verify OBS directly if its control connection was unavailable.

## Useful diagnostics

Safe integrated state:

```bash
bash bin/streamerctl status | python3 -m json.tool
```

Shareable/redacted:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

OBS:

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

Profiles:

```bash
python3 bin/profilectl.py status | python3 -m json.tool
```

Settings:

```bash
python3 bin/settings.py status | python3 -m json.tool
```

Audio:

```bash
python3 bin/audioctl.py status | python3 -m json.tool
```

## Before reporting a bug

Include the **redacted support snapshot**, the failing action, and a short description of what you expected versus what happened.

Do **not** post collaboration invites, room passwords, managed stream/control IDs, OBS WebSocket passwords, stream keys, full state directories, or other credentials in public issues.
