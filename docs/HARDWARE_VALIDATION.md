# Omarchy Streamer v1 Hardware Validation

This checklist is for the first real Omarchy Quattro machine and any later release-candidate validation pass.

The goal is to convert CI/protocol confidence into **field verification** without skipping privacy, recovery, or failure cases.

## 1. Clean install / update

- install Streamer through the normal Omarchy plugin flow
- confirm third-party review/enable behavior
- verify manifest reports `1.0.0`
- upgrade from an existing pre-1.0 Streamer state directory
- confirm `state-schema.json` appears
- confirm existing collaboration/profile/onboarding state is preserved
- confirm known state/config permissions are user-only
- confirm unknown user files in the Streamer state directory survive migration

## 2. Quattro shell / QML

- bar widget loads without QML errors
- popup opens/closes correctly
- right-click Streamer Mode toggle works
- control labels fit at normal scaling
- test vertical bar if available
- first-run overlay appears once on fresh onboarding state
- Skip/Finish suppress repeat first-run opening
- Guide replay works
- keyboard navigation / Escape behavior works as intended
- overlay focus does not strand keyboard input after closing

## 3. Settings

- default settings produce expected Stream-Safe workspace and guest scene
- set each supported preference through IPC
- verify invalid values are rejected
- verify file values persist across shell restart
- verify environment overrides win over file values
- reset one key and reset all settings
- verify a malformed settings file surfaces an error instead of silently falling back as if healthy

## 4. OBS lifecycle

- OBS missing -> correct warning
- Launch OBS
- authenticated WebSocket connection
- wrong/changed WebSocket password -> clear failure, no auth disabling
- Start/Stop Stream with a safe test provider/account
- Start/Stop Recording
- Start/Stop Replay Buffer
- Save Clip
- exact scene switching
- close/reopen OBS while Streamer remains loaded
- OBS crash/restart recovery
- verify Streamer never stores provider stream keys

## 5. Audio Desk

- enumerate built-in/USB/Bluetooth microphones available on the machine
- select a microphone
- mute/unmute
- volume +/-
- reconnect selected USB/Bluetooth device and verify node-name re-resolution
- unplug selected mic and verify MISSING warning
- confirm Streamer does not silently change desktop default input
- verify behavior after PipeWire/WirePlumber restart

## 6. Privacy and Stream-Safe

- enable Streamer Mode with DND initially OFF -> restore OFF after disable
- enable Streamer Mode with DND initially ON -> restore ON after disable
- simulate DND control failure -> Privacy must not claim success
- enter Stream-Safe from named and numeric workspaces
- return to previous workspace
- verify no windows are auto-moved/closed/hidden/killed
- trigger a default sensitive-app rule
- trigger a custom class/title rule
- verify active window titles do not appear in generic Streamer status

## 7. Emergency actions

### End Live + Mute

Verify best-effort attempts:

- Privacy/DND on
- selected microphone muted
- Stream-Safe entered
- live stream stopped

### Stop All Capture

Also verify:

- recording stopped
- replay buffer stopped

Repeat with one subsystem intentionally unavailable and confirm remaining safety steps still run.

## 8. Collaboration room / credentials

- Create Room
- Open Director
- Copy General Invite
- create/use all four managed slots
- Rotate Guest Link and verify old link no longer represents current slot identity
- Rotate Room and verify old room/slot links are obsolete
- Clear Room
- verify generic status never exposes password/streamId/controlId/secret URLs
- verify support snapshot also omits all collaboration identities

## 9. Real managed guest session

Use at least one separate physical device/browser as a guest; use two or more if available.

- send current managed invite
- guest joins successfully
- Streamer reports ONLINE only after callback
- close guest page -> OFFLINE after timeout/refresh
- suspend/background guest browser if possible -> observe honest stale/offline behavior
- network interruption -> CONTROL UNAVAILABLE rather than invented OFFLINE when appropriate
- remote Mute Guest
- remote Unmute Guest
- Disconnect Guest
- verify each cached state transition follows callback acknowledgement
- repeat after guest link rotation

## 10. OBS guest sources / layouts

- Add Group to OBS
- Add Guest 1-4 individually
- verify dedicated guest scene/source naming
- create an intentional reserved-name collision with a non-Browser Source and confirm Streamer refuses overwrite
- Auto layout with 1, 2, 3, and 4 managed guests
- Single
- Split
- Grid
- Focus Guest 1-4
- verify unrelated gameplay/webcam/logo/alert sources are untouched
- test at multiple OBS base canvas sizes if practical
- visually inspect cropping/scaling/alignment

## 11. Production Profiles

- Gaming -> 30 s refresh / auto layout recommendation
- Recording -> 30 s / auto
- Podcast -> 15 s / grid
- Low-spec -> 60 s / auto
- confirm profile selection alone does not mutate current OBS layout
- confirm Apply Profile Guest Layout is the separate visible-production action
- verify profile persists across shell restart

## 12. Support snapshot / diagnostics

Generate:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

Verify it does **not** reveal:

- current OBS scene name
- mic/device identity
- workspace/window identity
- sensitive-rule text
- collaboration room/password/IDs/URLs
- OBS WebSocket password
- stream keys
- raw error strings containing local details

Test `support.copy` and inspect the clipboard manually.

## 13. Sleep / wake / reconnect

With Streamer loaded:

- suspend/resume machine
- verify PipeWire state recovers
- verify OBS state recovers/reports honestly
- verify bar widget remains responsive
- verify collaboration cached state becomes stale rather than pretending fresh presence
- reconnect network
- reconnect USB/Bluetooth microphone
- close/reopen browser guest session

## 14. Multi-display / scaling

- one display
- two displays if available
- different scaling if available
- move focus/workspaces between displays
- verify Stream-Safe behavior
- verify popup/overlay placement and dimensions
- verify no panel content becomes inaccessible

## 15. Performance / coexistence

Measure at idle and during a real stream/recording session:

- CPU usage
- memory usage
- guest-refresh spikes
- OBS render/encoding health
- game FPS/frametime if testing a gaming profile
- thermal behavior
- audio dropouts

Compare Gaming and Low-spec profiles. Look specifically for the background guest-control polling cadence causing visible spikes.

## 16. Failure / recovery drills

- kill/restart OBS
- restart PipeWire/WirePlumber
- temporarily lose network
- guest provider unreachable
- invalid settings file
- unavailable `wl-copy`
- unavailable `xdg-open`
- unavailable `hyprctl`
- unavailable notification DND IPC

Every failure should surface honestly and avoid claiming a protection/action succeeded when it could not be confirmed.

## 17. Per-guest PipeWire discovery — observation only

Do **not** implement routing during the first observation pass.

With multiple real guests connected:

- inspect PipeWire/WirePlumber nodes/streams
- record which nodes appear/disappear with individual guest/browser sources
- determine whether any stable property maps one local audio stream to one managed remote guest
- test reconnect/browser refresh identity changes
- test OBS Browser Source versus provider Director audio topology

Only after a stable, repeatable identity strategy is demonstrated should per-guest routing be designed.

## 18. Screenshots / documentation

After the UI is physically verified:

- capture bar idle / STREAM / LIVE / REC states
- main popup
- Audio Desk
- Collaboration / managed guest state
- Profiles / layout controls
- Stream-Safe warning
- onboarding preflight
- sanitized support snapshot example

Use those real captures to update the user and troubleshooting manuals.

## Release decision

Do not label a capability **field verified** until the corresponding section above has been exercised on a real Omarchy machine. Automated CI remains necessary, but it is not a substitute for this pass.
