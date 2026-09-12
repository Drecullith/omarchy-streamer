#!/usr/bin/env python3
"""Validated user settings for Omarchy Streamer.

The settings file contains non-secret preferences only. Environment variables
remain supported as highest-priority overrides for development and recovery.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
CONFIG_ROOT = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy-streamer"
SETTINGS_FILE = CONFIG_ROOT / "settings.json"

DEFAULTS: dict[str, Any] = {
    "safeWorkspace": "stream-safe",
    "guestSceneName": "Omarchy Guests",
    "guestStateMaxAge": 30,
    "guestControlTimeout": 1.4,
    "sensitiveDefaults": True,
}

ENV_MAP = {
    "safeWorkspace": "OMARCHY_STREAMER_SAFE_WORKSPACE",
    "guestSceneName": "OMARCHY_STREAMER_GUEST_SCENE",
    "guestStateMaxAge": "OMARCHY_STREAMER_GUEST_STATE_MAX_AGE",
    "guestControlTimeout": "OMARCHY_STREAMER_VDO_API_TIMEOUT",
    "sensitiveDefaults": "OMARCHY_STREAMER_SENSITIVE_DEFAULTS",
}


class SettingsError(RuntimeError):
    pass


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise SettingsError("boolean value must be true/false")


def validate_value(key: str, value: Any) -> Any:
    if key == "safeWorkspace":
        text = str(value).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", text):
            raise SettingsError("safeWorkspace must be 1-64 letters, numbers, dots, underscores or hyphens")
        return text
    if key == "guestSceneName":
        text = str(value).strip()
        if not (1 <= len(text) <= 80) or any(ord(ch) < 32 for ch in text):
            raise SettingsError("guestSceneName must be 1-80 printable characters")
        return text
    if key == "guestStateMaxAge":
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise SettingsError("guestStateMaxAge must be an integer") from exc
        if not 10 <= number <= 600:
            raise SettingsError("guestStateMaxAge must be between 10 and 600 seconds")
        return number
    if key == "guestControlTimeout":
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise SettingsError("guestControlTimeout must be a number") from exc
        if not 0.25 <= number <= 15.0:
            raise SettingsError("guestControlTimeout must be between 0.25 and 15 seconds")
        return round(number, 3)
    if key == "sensitiveDefaults":
        return _parse_bool(value)
    raise SettingsError(f"unknown setting: {key}")


def ensure_config_dir() -> None:
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_ROOT.chmod(0o700)
    except OSError:
        pass


def load_file() -> dict[str, Any]:
    if not SETTINGS_FILE.is_file():
        return {}
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SettingsError(f"could not read settings: {exc}") from exc
    if not isinstance(raw, dict):
        raise SettingsError("settings file must contain a JSON object")
    schema = raw.get("schemaVersion", SCHEMA_VERSION)
    if schema != SCHEMA_VERSION:
        raise SettingsError(f"unsupported settings schemaVersion: {schema}")
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "schemaVersion":
            continue
        if key not in DEFAULTS:
            raise SettingsError(f"unknown setting in file: {key}")
        out[key] = validate_value(key, value)
    return out


def resolved() -> dict[str, Any]:
    file_values = load_file()
    values: dict[str, Any] = dict(DEFAULTS)
    values.update(file_values)
    sources = {key: ("file" if key in file_values else "default") for key in DEFAULTS}
    for key, env_name in ENV_MAP.items():
        if env_name in os.environ:
            values[key] = validate_value(key, os.environ[env_name])
            sources[key] = "environment"
    return {"schemaVersion": SCHEMA_VERSION, "values": values, "sources": sources}


def write_file(values: dict[str, Any]) -> None:
    ensure_config_dir()
    payload = {"schemaVersion": SCHEMA_VERSION, **values}
    temp = SETTINGS_FILE.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, SETTINGS_FILE)
        os.chmod(SETTINGS_FILE, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def set_value(key: str, raw_value: str) -> dict[str, Any]:
    if key not in DEFAULTS:
        raise SettingsError(f"unknown setting: {key}")
    current = load_file()
    current[key] = validate_value(key, raw_value)
    write_file(current)
    return {"ok": True, "action": "settings.set", "key": key, "value": current[key]}


def reset_value(key: str = "") -> dict[str, Any]:
    if key:
        if key not in DEFAULTS:
            raise SettingsError(f"unknown setting: {key}")
        current = load_file()
        current.pop(key, None)
        if current:
            write_file(current)
        else:
            try:
                SETTINGS_FILE.unlink()
            except FileNotFoundError:
                pass
        return {"ok": True, "action": "settings.reset", "key": key}
    try:
        SETTINGS_FILE.unlink()
    except FileNotFoundError:
        pass
    return {"ok": True, "action": "settings.reset", "key": ""}


def status() -> dict[str, Any]:
    try:
        data = resolved()
        return {"ready": True, **data, "error": ""}
    except SettingsError as exc:
        return {"ready": False, "schemaVersion": SCHEMA_VERSION, "values": dict(DEFAULTS), "sources": {k: "fallback" for k in DEFAULTS}, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer validated settings")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    set_cmd = sub.add_parser("set")
    set_cmd.add_argument("key")
    set_cmd.add_argument("value")
    reset_cmd = sub.add_parser("reset")
    reset_cmd.add_argument("key", nargs="?", default="")
    args = parser.parse_args()
    try:
        if args.command == "status":
            print(json.dumps(status(), separators=(",", ":")))
        elif args.command == "set":
            print(json.dumps(set_value(args.key, args.value), separators=(",", ":")))
        else:
            print(json.dumps(reset_value(args.key), separators=(",", ":")))
        return 0
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 14


if __name__ == "__main__":
    raise SystemExit(main())
