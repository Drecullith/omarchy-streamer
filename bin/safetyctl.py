#!/usr/bin/env python3
"""Stream-safe workspace and active-window guard for Omarchy Streamer.

Uses Hyprland's hyprctl JSON output and standard-library Python only.
It never closes, moves, hides, or kills user applications.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "omarchy-streamer"
PREVIOUS_WORKSPACE = STATE_DIR / "previous-workspace"
DEFAULT_RULES = Path(__file__).resolve().parent.parent / "config" / "sensitive-apps.txt"
USER_RULES = CONFIG_DIR / "sensitive-apps.txt"
SAFE_WORKSPACE = os.environ.get("OMARCHY_STREAMER_SAFE_WORKSPACE", "stream-safe")


class SafetyError(RuntimeError):
    pass


def run_hyprctl(*args: str) -> str:
    if shutil.which("hyprctl") is None:
        raise SafetyError("hyprctl is unavailable")
    result = subprocess.run(
        ["hyprctl", *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=1.5,
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip()
        raise SafetyError(msg or f"hyprctl {' '.join(args)} failed")
    return result.stdout.strip()


def hypr_json(command: str) -> dict[str, Any]:
    raw = run_hyprctl(command, "-j")
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise SafetyError(f"hyprctl {command} returned invalid JSON") from exc
    return value if isinstance(value, dict) else {}


def safe_workspace_name() -> str:
    name = SAFE_WORKSPACE.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
        raise SafetyError("invalid stream-safe workspace name")
    return name


def load_rules() -> list[tuple[str, str]]:
    rules: list[tuple[str, str]] = []
    paths = []
    if os.environ.get("OMARCHY_STREAMER_SENSITIVE_DEFAULTS", "1") != "0":
        paths.append(DEFAULT_RULES)
    paths.append(USER_RULES)

    for path in paths:
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kind = "any"
            pattern = line
            if ":" in line:
                prefix, rest = line.split(":", 1)
                if prefix.casefold() in {"class", "title", "any"}:
                    kind, pattern = prefix.casefold(), rest.strip()
            if pattern:
                rules.append((kind, pattern))
    return rules


def match_sensitive(window: dict[str, Any]) -> tuple[bool, str]:
    window_class = " ".join(
        str(window.get(key, "")) for key in ("class", "initialClass")
    ).casefold()
    window_title = " ".join(
        str(window.get(key, "")) for key in ("title", "initialTitle")
    ).casefold()

    for kind, pattern in load_rules():
        needle = pattern.casefold()
        if kind == "class" and needle in window_class:
            return True, f"class:{pattern}"
        if kind == "title" and needle in window_title:
            return True, f"title:{pattern}"
        if kind == "any" and (needle in window_class or needle in window_title):
            return True, f"any:{pattern}"
    return False, ""


def status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "ready": False,
        "workspaceName": "",
        "streamSafeActive": False,
        "sensitiveActive": False,
        "sensitiveRule": "",
        "activeWindowClass": "",
        "error": "",
    }
    try:
        workspace = hypr_json("activeworkspace")
        window = hypr_json("activewindow")
        workspace_name = str(workspace.get("name", ""))
        window_class = str(window.get("class") or window.get("initialClass") or "")
        sensitive, rule = match_sensitive(window)
        result.update(
            ready=True,
            workspaceName=workspace_name,
            streamSafeActive=(workspace_name == safe_workspace_name()),
            sensitiveActive=sensitive,
            sensitiveRule=rule,
            activeWindowClass=window_class,
        )
    except (SafetyError, OSError, subprocess.SubprocessError) as exc:
        result["error"] = str(exc)
    return result


def workspace_target(name: str) -> str:
    if re.fullmatch(r"-?\d+", name):
        return name
    if name.startswith("special:"):
        raise SafetyError("cannot restore a special workspace automatically")
    return f"name:{name}"


def workspace_enter() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    current = str(hypr_json("activeworkspace").get("name", ""))
    target_name = safe_workspace_name()
    if current == target_name:
        return {"ok": True, "workspace": target_name, "alreadyActive": True}
    if not current:
        raise SafetyError("could not determine the current workspace")
    if current.startswith("special:"):
        raise SafetyError("leave the special workspace before entering Stream-Safe")

    PREVIOUS_WORKSPACE.write_text(current + "\n", encoding="utf-8")
    try:
        PREVIOUS_WORKSPACE.chmod(0o600)
    except OSError:
        pass
    run_hyprctl("dispatch", "workspace", f"name:{target_name}")
    return {"ok": True, "workspace": target_name, "previousWorkspace": current}


def workspace_exit() -> dict[str, Any]:
    if not PREVIOUS_WORKSPACE.is_file():
        raise SafetyError("no previous workspace has been recorded")
    previous = PREVIOUS_WORKSPACE.read_text(encoding="utf-8").strip()
    if not previous:
        raise SafetyError("recorded previous workspace is empty")
    run_hyprctl("dispatch", "workspace", workspace_target(previous))
    try:
        PREVIOUS_WORKSPACE.unlink()
    except FileNotFoundError:
        pass
    return {"ok": True, "workspace": previous}


def perform(action: str) -> dict[str, Any]:
    if action == "workspace.enter":
        return workspace_enter()
    if action == "workspace.exit":
        return workspace_exit()
    if action in {"safety.refresh", "window.check"}:
        return status()
    raise SafetyError(f"unsupported safety action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer stream-safety controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    args = parser.parse_args()

    try:
        payload = status() if args.command == "status" else perform(args.name)
        print(json.dumps(payload, separators=(",", ":")))
        return 0
    except (SafetyError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
