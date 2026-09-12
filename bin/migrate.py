#!/usr/bin/env python3
"""One-time, non-destructive state migration for Omarchy Streamer v1.

The migration never deletes unknown user files. It repairs permissions on known
Streamer state/config files and writes a schema marker for future upgrades.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

STATE_SCHEMA_VERSION = 1
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
CONFIG_ROOT = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy-streamer"
MARKER = STATE_ROOT / "state-schema.json"

KNOWN_STATE_FILES = (
    "collab-session.json",
    "collab-guest-state.json",
    "onboarding.json",
    "profile.json",
    "previous-workspace",
    "previous-dnd",
    "active",
    "privacy",
)
KNOWN_CONFIG_FILES = ("settings.json", "sensitive-apps.txt")


def _chmod(path: Path, mode: int) -> bool:
    if not path.exists():
        return False
    try:
        if path.stat().st_mode & 0o777 != mode:
            path.chmod(mode)
            return True
    except OSError:
        return False
    return False


def _write_marker() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    temp = MARKER.with_suffix(".tmp")
    payload = {"schemaVersion": STATE_SCHEMA_VERSION}
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, MARKER)
        os.chmod(MARKER, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def marker_version() -> int:
    if not MARKER.is_file():
        return 0
    try:
        value: Any = json.loads(MARKER.read_text(encoding="utf-8"))
        return int(value.get("schemaVersion", 0)) if isinstance(value, dict) else 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 0


def migrate() -> dict[str, Any]:
    current = marker_version()
    if current > STATE_SCHEMA_VERSION:
        return {"ok": False, "schemaVersion": current, "changed": 0, "error": "state schema is newer than this Streamer build"}

    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    changed = 0
    changed += int(_chmod(STATE_ROOT, 0o700))
    changed += int(_chmod(CONFIG_ROOT, 0o700))
    for name in KNOWN_STATE_FILES:
        changed += int(_chmod(STATE_ROOT / name, 0o600))
    for name in KNOWN_CONFIG_FILES:
        changed += int(_chmod(CONFIG_ROOT / name, 0o600))

    # Existing collaboration rooms from v0.5 are migrated lazily by collabctl
    # so no secret material needs to be duplicated here.
    _write_marker()
    return {"ok": True, "schemaVersion": STATE_SCHEMA_VERSION, "changed": changed, "error": ""}


def main() -> int:
    result = migrate()
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["ok"] else 15


if __name__ == "__main__":
    raise SystemExit(main())
