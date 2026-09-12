# Omarchy Streamer Troubleshooting

This guide covers common v0.7 symptoms. Start with the plugin's own status before changing system configuration.

```bash
bash ~/.config/omarchy/plugins/io.github.drecullith.streamer/bin/streamerctl status | python3 -m json.tool
```

If your plugin directory differs, run the same `bin/streamerctl status` from the installed plugin root.

## The Stream widget is missing

Check that the plugin is installed and enabled:

```bash
omarchy plugin enable io.github.drecullith.streamer
```

If the shell was already running during an unusual install/update state, reload/restart the Omarchy shell using the normal Omarchy workflow and check again.

## The first-run guide did not appear

Open it manually:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.open tour
```

Check onboarding state:

```bash
python3 bin/onboardingctl.py status | python3 -m json.tool
```

To deliberately re-enable first-run eligibility:

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

The service intentionally attempts the automatic first-run summon only once per shell session.

## OBS says missing

Check whether the `obs` executable is on PATH:

```bash
command -v obs
```

Streamer does not install OBS automatically.

## OBS is running but WebSocket is unavailable

Check the Streamer status:

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

Confirm OBS WebSocket is enabled and password authentication remains configured in OBS. Streamer normally reads OBS's local obs-websocket config and connects to localhost.

The default port is 4455 unless OBS is configured differently.

Do not disable authentication merely to make Streamer connect.

## OBS control reports an authentication error

Streamer uses OBS's configured WebSocket password. If OBS's configuration was changed while OBS/Streamer was running, restart or reload the relevant application state and check again.

The plugin does not store the OBS password in the repository or its normal state directory.

## Start Stream fails

Open OBS and verify that the streaming service/output settings work directly in OBS first. Streamer asks OBS to start the configured stream; it does not create provider credentials or stream keys.

## Save Clip fails

The replay buffer must be running.

Use **Start Replay Buffer** first. If that fails, verify replay-buffer settings in OBS.

## Scene switching fails

Use the exact OBS scene name. Scene matching is not fuzzy.

Check current OBS status:

```bash
python3 bin/obsws.py status | python3 -m json.tool
```

## PipeWire is not detected

Check:

```bash
pgrep -x pipewire
command -v wpctl
```

Audio Desk requires WirePlumber's `wpctl` interface.

## No microphone appears

Inspect the Audio Desk status:

```bash
python3 bin/audioctl.py status | python3 -m json.tool
```

Reconnect the device if necessary, then refresh the panel. Bluetooth/USB devices can receive new PipeWire numeric IDs after reconnecting; Streamer resolves the remembered node name again rather than trusting an old ID.

## The selected microphone says MISSING

Streamer will not silently substitute another microphone.

Use **Next Mic / Select Mic** to deliberately choose an available source.

## Microphone mute/volume controls fail

Confirm `wpctl` is present and the selected source is still available:

```bash
command -v wpctl
python3 bin/audioctl.py status | python3 -m json.tool
```

## Privacy will not turn on

Privacy depends on Omarchy notification DND being reachable.

Check:

```bash
omarchy-shell notifications dndState
```

Expected output is `on` or `off`.

If the state is unavailable/unknown, Streamer deliberately does not claim Privacy is enabled.

## Privacy changed my notification setting

When Streamer enables Privacy, it records the previous DND state and restores it when Privacy/Streamer Mode is disabled.

If a shell crash or manual file manipulation interrupted that lifecycle, inspect:

```text
~/.local/state/omarchy-streamer/
```

Do not delete state files while Streamer Mode is active unless you understand the restoration consequence.

## Stream-Safe is unavailable

Check Hyprland control:

```bash
command -v hyprctl
hyprctl activeworkspace -j
```

Then query:

```bash
python3 bin/safetyctl.py status | python3 -m json.tool
```

## Stream-Safe did not move my windows

That is intentional. Stream-Safe switches to a dedicated workspace but does not automatically move, hide, close, or kill existing windows.

## I received a sensitive-window warning

The warning is advisory. Streamer will not manipulate the matched application.

Review default rules in:

```text
config/sensitive-apps.txt
```

Personal rules can be placed in:

```text
~/.config/omarchy-streamer/sensitive-apps.txt
```

## Collaboration says `wl-copy` missing

`wl-copy` is needed only for copying guest/source links through the panel.

Check:

```bash
command -v wl-copy
```

Streamer will report the missing helper instead of silently installing it.

## Open Director is unavailable

Check:

```bash
command -v xdg-open
```

The browser director launch uses `xdg-open`.

## A guest invite stopped working after rotation

That is expected. **Rotate Guest Link** invalidates that managed slot's old private identities. **Rotate Room** replaces the room and all managed guest identities.

Send the newly copied invite.

## Add Guest to OBS fails

First confirm OBS WebSocket is connected.

Then verify the Browser Source provisioning layer through the automated behavior expected by `bin/obsbrowser.py`.

Streamer manages these reserved names:

```text
Omarchy Streamer - Guests
Omarchy Streamer - Guest 1
Omarchy Streamer - Guest 2
Omarchy Streamer - Guest 3
Omarchy Streamer - Guest 4
```

If a reserved name already belongs to a non-Browser Source, Streamer refuses to replace it. Rename/remove the conflicting source yourself if it is safe to do so.

## The emergency button reports partial success

Emergency actions are best-effort by design. They attempt each safety step independently.

After using an emergency action, verify OBS capture state directly if the OBS connection itself was unavailable.

## Generic status contains collaboration secrets

It should not. Treat that as a security bug.

Normal status must not contain fields such as room passwords, managed stream IDs, private page-control IDs, or secret guest/source URLs.

The CI suite explicitly checks this boundary.

## Reset only onboarding

```bash
omarchy-shell io.github.drecullith.streamer action onboarding.reset ""
```

This does not reset OBS, Audio Desk, collaboration rooms, Stream-Safe configuration, or Streamer Mode.

## Clear only collaboration credentials

Use **Clear Room** in the panel or:

```bash
omarchy-shell io.github.drecullith.streamer action collab.reset ""
```

This removes the locally stored collaboration session.

## Diagnostic commands

General state:

```bash
bash bin/streamerctl doctor | python3 -m json.tool
```

OBS:

```bash
python3 bin/obsws.py status | python3 -m json.tool
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
- the failing action name
- sanitized error/status output

Do **not** post collaboration invite URLs, room passwords, OBS WebSocket passwords, stream keys, or other credentials in public bug reports.
