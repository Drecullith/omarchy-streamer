# Security Policy

Omarchy Streamer is user-level software that coordinates streaming, recording, desktop audio, privacy state, OBS, and browser collaboration. Security and privacy issues can expose more than ordinary application state, so reports should avoid publishing sensitive data.

## Supported version

The current supported line is **1.x**. Older pre-1.0 milestones were development snapshots and are not treated as independently supported release lines.

## Security invariants

Omarchy Streamer is designed so that it does not:

- require root or implicit `sudo`,
- silently install packages,
- change firewall rules,
- run a collaboration listener/server,
- store streaming-service stream keys,
- expose collaboration room passwords, stream IDs, page-control IDs, or secret URLs in generic collaboration status,
- place private managed guest-control IDs on process command lines,
- disable OBS WebSocket authentication,
- hand external integrations unrestricted shell execution,
- silently substitute missing microphones,
- auto-close/hide sensitive applications.

High-impact actions are explicitly marked in `contracts/actions-v1.json` so callers can require confirmation.

## Reporting a suspected vulnerability

Do **not** post passwords, room/invite links, managed stream/control IDs, OBS WebSocket credentials, stream keys, or a whole Streamer state directory in a public issue.

If GitHub private vulnerability reporting is available for this repository, use the repository's **Security** tab. If it is not available, open only a minimal public issue stating that you found a security issue and need a private reporting channel; do not include exploit details or credentials in that issue.

For ordinary bugs, prefer the privacy-safe support snapshot:

```bash
bash bin/streamerctl support | python3 -m json.tool
```

or:

```bash
omarchy-shell io.github.drecullith.streamer action support.copy ""
```

The support snapshot intentionally omits scene names, mic/device identities, window/workspace names, sensitive-window rule text, collaboration credentials/IDs/URLs, OBS passwords, stream keys, and raw error text.

## Collaboration credentials

Managed collaboration state is stored locally with restrictive user-only permissions where supported. Secret-bearing links leave Streamer only through explicit copy/open actions.

Rotating a managed Guest slot replaces that slot's private stream/control identities. Rotating a room replaces the room and all slot identities. Clearing the room deletes locally stored collaboration session credentials.

## Dependency boundary

Streamer reports missing dependencies instead of installing them. OBS remains authoritative for its output/provider configuration, and PipeWire/WirePlumber remain authoritative for local audio topology.

## Field-validation status

The v1 codebase is CI-hardened, but real hardware/browser-session validation is still pending. Provider callback behavior, OBS RPC, WirePlumber behavior, Hyprland behavior, and secret/redaction boundaries have automated fake-adapter coverage; those tests do not replace real-machine validation.
