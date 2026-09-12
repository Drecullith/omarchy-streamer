# Changelog

All notable Omarchy Streamer milestones are summarized here.

## 1.0.0 — 2026-09-12

Release-hardening milestone.

### Added

- schema-versioned validated user settings
- central settings injection for Stream-Safe, guest scene, guest freshness, guest-control timeout, and default sensitive-window rules
- one-time non-destructive state/permission migration
- privacy-safe support snapshot and clipboard action
- support-snapshot redaction tests seeded with fake secrets and identifying production names
- action-ID uniqueness and v1 release invariants in CI
- v1 hardware-validation checklist
- security/reporting guidance

### Hardened

- Streamer mode/privacy marker permissions
- service IPC coverage for settings, migration, and support actions
- exact manifest/status version checks
- public documentation and troubleshooting for v1

### Validation boundary

v1.0.0 is code-complete and CI-hardened. Real Omarchy Quattro, OBS, PipeWire, Hyprland, microphone, multi-display, sleep/wake, performance, and live browser-guest validation remain pending on physical hardware.

## 0.9.0

- Production Profiles: Gaming, Recording, Podcast, Low-spec
- profile-aware managed-guest refresh cadence
- managed guest OBS layouts: auto, single, split, grid, focus
- explicit separation between profile selection and visible OBS layout mutation

## 0.8.0

- callback-backed managed guest presence
- ONLINE / OFFLINE / UNKNOWN / STALE state
- remote managed-guest mic control
- managed-guest disconnect
- correlated callback/timeouts and concurrent guest refresh

## 0.7.0

- native Quattro guided onboarding overlay
- first-run walkthrough and replayable Guide
- live preflight page
- full user guide and troubleshooting manual

## 0.6.0

- four managed guest slots
- stable per-slot guest identity/control capability
- per-slot invites and OBS URLs
- one-click managed Browser Source provisioning

## 0.5.0

- browser collaboration rooms
- director/invite/group-source workflow
- local credential storage and secret-bearing action boundary

## 0.4.0

- Stream-Safe workspace
- warning-only sensitive-window guard
- End Live + Mute
- Stop All Capture

## 0.3.0

- PipeWire/WirePlumber Audio Desk
- remembered microphone selection
- mic mute/unmute and volume controls
- missing-device warnings

## 0.2.0

- authenticated OBS WebSocket v5 adapter
- stream, record, replay-buffer, clip, and scene control
- live OBS state in the Streamer panel

## 0.1.0

- Omarchy Quattro plugin foundation
- service + bar widget
- explicit local IPC/action contract
- reversible Streamer Mode and notification privacy state
- CI smoke-test baseline
