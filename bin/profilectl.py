#!/usr/bin/env python3
"""Production profile state for Omarchy Streamer.

Profiles are intentionally non-destructive. Selecting one stores production
preferences; it never starts/stops capture or changes streaming credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
PROFILE_FILE = STATE_ROOT / "profile.json"

PROFILES: dict[str, dict[str, Any]] = {
    "gaming": {
        "label": "Gaming",
        "guestRefreshSeconds": 30,
        "guestLayout": "auto",
        "privacyRecommended": True,
        "description": "Balanced live gameplay with moderate guest polling.",
    },
    "recording": {
        "label": "Recording",
        "guestRefreshSeconds": 30,
        "guestLayout": "auto",
        "privacyRecommended": True,
        "description": "Local recording-focused session with quiet background activity.",
    },
    "podcast": {
        "label": "Podcast",
        "guestRefreshSeconds": 15,
        "guestLayout": "grid",
        "privacyRecommended": True,
        "description": "Guest-focused production with faster collaborator health refresh.",
    },
    "low-spec": {
        "label": "Low-spec",
        "guestRefreshSeconds": 60,
        "guestLayout": "auto",
        "privacyRecommended": True,
        "description": "Reduced background polling for constrained or gaming-heavy systems.",
    },
}
DEFAULT_PROFILE = "gaming"


class ProfileError(RuntimeError):
    pass


def ensure_state_dir() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try: STATE_ROOT.chmod(0o700)
    except OSError: pass


def save_profile(name: str) -> None:
    if name not in PROFILES:
        raise ProfileError(f"unknown profile: {name}")
    ensure_state_dir()
    temp = PROFILE_FILE.with_suffix(".tmp")
    payload = json.dumps({"profile": name, "selectedAt": int(time.time())}, separators=(",", ":")) + "\n"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, PROFILE_FILE)
        os.chmod(PROFILE_FILE, 0o600)
    finally:
        try: temp.unlink()
        except FileNotFoundError: pass


def current_name() -> str:
    if not PROFILE_FILE.is_file():
        return DEFAULT_PROFILE
    try:
        value = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PROFILE
    name = str(value.get("profile", "")) if isinstance(value, dict) else ""
    return name if name in PROFILES else DEFAULT_PROFILE


def status() -> dict[str, Any]:
    current = current_name()
    order = list(PROFILES)
    return {
        "ready": True,
        "active": current,
        "activeLabel": PROFILES[current]["label"],
        "guestRefreshSeconds": int(PROFILES[current]["guestRefreshSeconds"]),
        "guestLayout": str(PROFILES[current]["guestLayout"]),
        "privacyRecommended": bool(PROFILES[current]["privacyRecommended"]),
        "profiles": [{"id": name, **value} for name, value in PROFILES.items()],
        "order": order,
        "error": "",
    }


def perform(action: str, value: str = "") -> dict[str, Any]:
    names = list(PROFILES)
    current = current_name()
    if action == "profile.apply":
        target = value.strip().lower()
        if target not in PROFILES:
            raise ProfileError("profile must be gaming, recording, podcast, or low-spec")
    elif action == "profile.next":
        target = names[(names.index(current) + 1) % len(names)]
    elif action == "profile.previous":
        target = names[(names.index(current) - 1) % len(names)]
    else:
        raise ProfileError(f"unsupported profile action: {action}")
    save_profile(target)
    return {"ok": True, "action": action, "profile": target, "label": PROFILES[target]["label"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer production profiles")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    action.add_argument("value", nargs="?", default="")
    args = parser.parse_args()
    try:
        result = status() if args.command == "status" else perform(args.name, args.value)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 13


if __name__ == "__main__":
    raise SystemExit(main())
