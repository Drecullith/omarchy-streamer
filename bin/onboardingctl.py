#!/usr/bin/env python3
"""First-run onboarding state for Omarchy Streamer.

This controller stores only whether the current onboarding tour has been
completed. It deliberately contains no streaming, collaboration, or device
credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

TOUR_VERSION = 1
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
STATE_FILE = STATE_ROOT / "onboarding.json"


class OnboardingError(RuntimeError):
    pass


def ensure_state_dir() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        STATE_ROOT.chmod(0o700)
    except OSError:
        pass


def read_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {}
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OnboardingError(f"could not read onboarding state: {exc}") from exc
    return value if isinstance(value, dict) else {}


def status() -> dict[str, Any]:
    error = ""
    try:
        state = read_state()
    except OnboardingError as exc:
        state = {}
        error = str(exc)

    completed_version = int(state.get("version", 0) or 0)
    completed = completed_version >= TOUR_VERSION
    completed_at = state.get("completedAt") if completed else None
    return {
        "ready": True,
        "tourVersion": TOUR_VERSION,
        "completed": completed,
        "completedAt": completed_at,
        "error": error,
    }


def complete() -> dict[str, Any]:
    ensure_state_dir()
    payload = {
        "version": TOUR_VERSION,
        "completedAt": int(time.time()),
    }
    temp = STATE_FILE.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, STATE_FILE)
        os.chmod(STATE_FILE, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    return {"ok": True, "action": "onboarding.complete", "tourVersion": TOUR_VERSION}


def reset() -> dict[str, Any]:
    try:
        STATE_FILE.unlink()
    except FileNotFoundError:
        pass
    return {"ok": True, "action": "onboarding.reset", "tourVersion": TOUR_VERSION}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer onboarding state controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print(json.dumps(status(), separators=(",", ":")))
        elif args.name == "onboarding.complete":
            print(json.dumps(complete(), separators=(",", ":")))
        elif args.name == "onboarding.reset":
            print(json.dumps(reset(), separators=(",", ":")))
        else:
            raise OnboardingError(f"unsupported onboarding action: {args.name}")
        return 0
    except OnboardingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 11


if __name__ == "__main__":
    raise SystemExit(main())
