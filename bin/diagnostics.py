#!/usr/bin/env python3
"""Build a privacy-safe Omarchy Streamer support snapshot from normal status.

This intentionally omits scene names, microphone identities, window classes,
workspace names, collaboration URLs/IDs/passwords, and raw error strings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"


def _bool(value: Any) -> bool:
    return bool(value)


def build_snapshot(status: dict[str, Any], settings: dict[str, Any] | None = None) -> dict[str, Any]:
    if not settings and isinstance(status.get("settings"), dict):
        settings = status["settings"]
    settings = settings or {}
    obs = status.get("obsWebSocket") if isinstance(status.get("obsWebSocket"), dict) else {}
    audio = status.get("audio") if isinstance(status.get("audio"), dict) else {}
    safety = status.get("safety") if isinstance(status.get("safety"), dict) else {}
    collab = status.get("collaboration") if isinstance(status.get("collaboration"), dict) else {}
    onboarding = status.get("onboarding") if isinstance(status.get("onboarding"), dict) else {}
    profiles = status.get("profiles") if isinstance(status.get("profiles"), dict) else {}
    guests = collab.get("guests") if isinstance(collab.get("guests"), list) else []

    online = sum(1 for g in guests if isinstance(g, dict) and g.get("online") is True and not g.get("stale"))
    offline = sum(1 for g in guests if isinstance(g, dict) and g.get("online") is False)
    stale = sum(1 for g in guests if isinstance(g, dict) and g.get("stale") is True)
    unknown = max(0, len(guests) - online - offline)

    version = "unknown"
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        version = str(manifest.get("version", "unknown"))
    except (OSError, json.JSONDecodeError):
        pass

    values = settings.get("values", {}) if isinstance(settings.get("values"), dict) else {}
    sources = settings.get("sources", {}) if isinstance(settings.get("sources"), dict) else {}

    return {
        "schemaVersion": 1,
        "version": version,
        "statusVersion": int(status.get("version", 0) or 0),
        "streamer": {"active": _bool(status.get("active")), "privacy": _bool(status.get("privacy")), "dndKnown": str(status.get("dndState", "unknown")) in {"on", "off"}},
        "dependencies": {
            "python": _bool(status.get("pythonReady")),
            "obsInstalled": _bool(status.get("obsInstalled")),
            "obsRunning": _bool(status.get("obsRunning")),
            "obsWebSocket": _bool(obs.get("connected")),
            "pipewire": _bool(status.get("pipewireReady")),
            "wpctl": _bool(status.get("wpctlInstalled")),
            "streamSafe": _bool(safety.get("ready")),
            "collaboration": _bool(collab.get("ready")),
            "guestControl": _bool(collab.get("guestControlReady")),
        },
        "capture": {"streaming": obs.get("streaming"), "recording": obs.get("recording"), "replayBuffer": obs.get("replayBuffer")},
        "audio": {"ready": _bool(audio.get("ready")), "selectedPresent": _bool(audio.get("selectedPresent")), "muted": audio.get("muted"), "volumeKnown": audio.get("volumePercent") is not None},
        "safety": {"streamSafeActive": _bool(safety.get("streamSafeActive")), "sensitiveWarning": _bool(safety.get("sensitiveActive"))},
        "collaboration": {"active": _bool(collab.get("active")), "slotCount": int(collab.get("slotCount", 0) or 0), "onlineFresh": online, "offline": offline, "unknown": unknown, "stale": stale},
        "profile": {"active": str(profiles.get("active", "")), "guestRefreshSeconds": int(profiles.get("guestRefreshSeconds", 0) or 0)},
        "onboarding": {"ready": _bool(onboarding.get("ready")), "complete": _bool(onboarding.get("completed"))},
        "settings": {
            "ready": bool(settings.get("ready", False)),
            "guestStateMaxAge": int(values.get("guestStateMaxAge", 0) or 0),
            "guestControlTimeout": float(values.get("guestControlTimeout", 0) or 0),
            "sources": {key: str(value) for key, value in sources.items()},
        },
        "redaction": "No scene names, mic identities, window/workspace names, URLs, room credentials, guest IDs, OBS passwords, stream keys, or raw error text are included.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a sanitized Omarchy Streamer support snapshot")
    parser.add_argument("--settings", default="", help="optional settings-status JSON string")
    args = parser.parse_args()
    try:
        status = json.load(sys.stdin)
        if not isinstance(status, dict):
            raise ValueError("status must be a JSON object")
        settings = json.loads(args.settings) if args.settings else None
        if settings is not None and not isinstance(settings, dict):
            raise ValueError("settings must be a JSON object")
        print(json.dumps(build_snapshot(status, settings), separators=(",", ":"), sort_keys=True))
        return 0
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: could not build support snapshot: {exc}", file=sys.stderr)
        return 16


if __name__ == "__main__":
    raise SystemExit(main())
