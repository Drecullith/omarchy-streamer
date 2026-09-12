#!/usr/bin/env python3
"""Run one Streamer adapter with validated settings exported as env vars."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def load_settings():
    path = Path(__file__).with_name("settings.py")
    spec = importlib.util.spec_from_file_location("omarchy_streamer_settings", path)
    if not spec or not spec.loader:
        raise RuntimeError("could not load Streamer settings")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configured_environment() -> dict[str, str]:
    module = load_settings()
    data = module.resolved()
    values = data["values"]
    env = dict(os.environ)
    mapping = {
        "safeWorkspace": "OMARCHY_STREAMER_SAFE_WORKSPACE",
        "guestSceneName": "OMARCHY_STREAMER_GUEST_SCENE",
        "guestStateMaxAge": "OMARCHY_STREAMER_GUEST_STATE_MAX_AGE",
        "guestControlTimeout": "OMARCHY_STREAMER_VDO_API_TIMEOUT",
        "sensitiveDefaults": "OMARCHY_STREAMER_SENSITIVE_DEFAULTS",
    }
    for key, name in mapping.items():
        if name in os.environ:
            continue
        value = values[key]
        if isinstance(value, bool):
            env[name] = "1" if value else "0"
        else:
            env[name] = str(value)
    return env


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: withsettings.py <command> [args...]", file=sys.stderr)
        return 14
    try:
        result = subprocess.run(sys.argv[1:], env=configured_environment(), check=False)
        return int(result.returncode)
    except Exception as exc:
        print(f"error: invalid Streamer settings: {exc}", file=sys.stderr)
        return 14


if __name__ == "__main__":
    raise SystemExit(main())
