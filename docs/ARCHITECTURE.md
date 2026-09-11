# Omarchy Streamer architecture

## Goal

Omarchy Streamer is a third-party Omarchy Quattro plugin that turns a normal desktop session into a deliberate streaming/recording workspace without hiding privileged actions or taking permanent ownership of user settings.

The initial architecture has three layers:

1. `BarWidget.qml` — user-facing status and fast controls.
2. `Service.qml` — long-lived Quickshell service and IPC boundary.
3. `bin/streamerctl` — small user-level controller for OS/process state and reversible privacy changes.

## Core invariants

- No root requirement.
- No implicit `sudo`.
- No package manager invocation.
- Missing dependencies are reported, not silently installed.
- State changed by Streamer Mode must be restorable when the mode is disabled.
- Broadcast-affecting actions have stable names and are exposed through one action contract.
- Future automation or external control must call the same explicit actions as the UI; integrations do not get a hidden privileged path.
- Starting/stopping a stream, recording, changing a live scene, launching OBS, or unmuting a microphone must remain permission-aware for external automation.

## State

Runtime state is stored under:

`$XDG_STATE_HOME/omarchy-streamer/`

or, when `XDG_STATE_HOME` is unset:

`~/.local/state/omarchy-streamer/`

v0.1 uses marker files for active mode and privacy state, plus a snapshot of the notification DND state that existed before Streamer Privacy was enabled.

This makes notification suppression reversible. If DND was already on before Streamer Mode, disabling Streamer Mode leaves it on.

## IPC

The Quickshell service registers:

`io.github.drecullith.streamer`

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

The stable action vocabulary is documented in `contracts/actions-v1.json`.

External integrations should use this same IPC boundary rather than separate command paths. Broadcast-affecting actions remain explicit, observable, and permission-aware.

## OBS integration roadmap

v0.1 deliberately limits OBS automation to detection and launch. It does not guess at third-party command-line syntax.

The next adapter should speak to OBS WebSocket directly or through a small audited local client and implement:

- stream start/stop
- recording start/stop
- replay-buffer save
- scene switching
- encoder/bitrate/connection health

The OBS adapter should remain replaceable and must never contain stream keys or service credentials in repository files.

## Audio roadmap

PipeWire is treated as the native audio layer. Future audio controls will use explicit device/node identities and should support:

- microphone mute/unmute
- microphone selection
- per-source monitoring
- collaborator/game/browser routing
- health warnings when the configured source disappears

## Privacy roadmap

v0.1 integrates with Omarchy notification DND and restores the user's prior DND state. Later protections may include:

- notification history suppression during capture
- stream-safe workspaces
- sensitive-window warnings
- clipboard-popup suppression
- optional screen-share allowlists

Privacy protections should fail safe and visibly report when a requested protection could not be applied.

## Mode700 and collaboration

Mode700 is a later communication integration, not a hard dependency. Omarchy Streamer should expose collaborator presence and room controls through adapters so Mode700, browser-based guests, or other collaboration tools can be swapped without changing the core mode lifecycle.
