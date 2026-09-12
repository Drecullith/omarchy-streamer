#!/usr/bin/env python3
"""PipeWire/WirePlumber audio controller for Omarchy Streamer.

Uses wpctl only. A chosen microphone is stored by PipeWire node name so the
selection can survive node-id changes. Selecting a microphone here does not
silently change the desktop-wide default source.
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


def state_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return root / "omarchy-streamer" / "audio.json"


def run_wpctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["wpctl", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=2.0,
        check=False,
    )


def load_state() -> dict[str, Any]:
    path = state_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_selected(name: str) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"selectedSourceName": name}, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temp, path)


def list_sources() -> tuple[list[dict[str, Any]], str]:
    if shutil.which("wpctl") is None:
        return [], "wpctl is not installed"

    proc = run_wpctl("list", "audio", "sources")
    if proc.returncode != 0:
        message = proc.stderr.strip() or proc.stdout.strip() or "wpctl could not list audio sources"
        return [], message

    sources: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        fields = [part.strip() for part in raw.split("\t")]
        if len(fields) < 2:
            # Compatibility fallback for versions that render whitespace columns.
            match = re.match(r"^\s*\*?\s*(\d+)\s+(.+?)\s*$", raw)
            if not match:
                continue
            object_id, name = match.group(1), match.group(2)
            default = raw.lstrip().startswith("*")
        else:
            object_id = fields[0].lstrip("* ")
            name = fields[1]
            default = any(part == "*" for part in fields) or fields[0].startswith("*")
        if not object_id.isdigit() or not name:
            continue
        sources.append({"id": int(object_id), "name": name, "default": default})

    return sources, ""


def selected_source(sources: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str, bool]:
    saved = str(load_state().get("selectedSourceName", "")).strip()
    if saved:
        for source in sources:
            if source["name"] == saved:
                return source, saved, True
        return None, saved, False

    for source in sources:
        if source.get("default"):
            return source, str(source["name"]), True
    if sources:
        return sources[0], str(sources[0]["name"]), True
    return None, "", False


def get_volume(object_id: int) -> tuple[int | None, bool | None, str]:
    proc = run_wpctl("get-volume", str(object_id))
    if proc.returncode != 0:
        return None, None, proc.stderr.strip() or "could not read microphone volume"
    text = proc.stdout.strip()
    match = re.search(r"Volume:\s*([0-9]+(?:\.[0-9]+)?)", text)
    volume = round(float(match.group(1)) * 100) if match else None
    muted = "[MUTED]" in text.upper()
    return volume, muted, ""


def status() -> dict[str, Any]:
    sources, error = list_sources()
    selected, selected_name, present = selected_source(sources)
    volume: int | None = None
    muted: bool | None = None
    detail_error = ""
    if selected is not None:
        volume, muted, detail_error = get_volume(int(selected["id"]))

    if not error and detail_error:
        error = detail_error
    if selected_name and not present and not error:
        error = f"selected microphone is unavailable: {selected_name}"

    return {
        "ready": shutil.which("wpctl") is not None and not bool(error and not sources),
        "sources": sources,
        "selectedSourceName": selected_name,
        "selectedSourceId": selected.get("id") if selected else None,
        "selectedPresent": present,
        "muted": muted,
        "volumePercent": volume,
        "error": error,
    }


def require_selected() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sources, error = list_sources()
    if error and not sources:
        raise RuntimeError(error)
    selected, saved, present = selected_source(sources)
    if selected is None or not present:
        if saved:
            raise RuntimeError(f"selected microphone is unavailable: {saved}")
        raise RuntimeError("no microphone source is available")
    return sources, selected


def select(value: str) -> dict[str, Any]:
    value = value.strip()
    if not value:
        raise RuntimeError("mic.select requires a source name or id")
    sources, error = list_sources()
    if error and not sources:
        raise RuntimeError(error)
    chosen = next((source for source in sources if source["name"] == value or str(source["id"]) == value), None)
    if chosen is None:
        raise RuntimeError(f"microphone source not found: {value}")
    save_selected(str(chosen["name"]))
    return {"ok": True, "selectedSourceName": chosen["name"], "selectedSourceId": chosen["id"]}


def select_next() -> dict[str, Any]:
    sources, error = list_sources()
    if error and not sources:
        raise RuntimeError(error)
    if not sources:
        raise RuntimeError("no microphone source is available")
    selected, _, present = selected_source(sources)
    if selected is None or not present:
        chosen = sources[0]
    else:
        index = next((i for i, source in enumerate(sources) if source["name"] == selected["name"]), -1)
        chosen = sources[(index + 1) % len(sources)]
    save_selected(str(chosen["name"]))
    return {"ok": True, "selectedSourceName": chosen["name"], "selectedSourceId": chosen["id"]}


def set_mute(value: str) -> dict[str, Any]:
    _, selected = require_selected()
    proc = run_wpctl("set-mute", str(selected["id"]), value)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to change microphone mute state")
    return {"ok": True, "selectedSourceName": selected["name"], "mute": value}


def set_volume(value: str) -> dict[str, Any]:
    try:
        percent = int(value)
    except ValueError as exc:
        raise RuntimeError("mic.volume requires an integer percentage") from exc
    if not 0 <= percent <= 150:
        raise RuntimeError("mic.volume must be between 0 and 150 percent")
    _, selected = require_selected()
    proc = run_wpctl("set-volume", str(selected["id"]), f"{percent}%")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to change microphone volume")
    return {"ok": True, "selectedSourceName": selected["name"], "volumePercent": percent}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer PipeWire audio controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    action.add_argument("value", nargs="?", default="")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print(json.dumps(status(), separators=(",", ":")))
            return 0

        if args.name == "mic.select":
            result = select(args.value)
        elif args.name == "mic.next":
            result = select_next()
        elif args.name == "mic.mute":
            result = set_mute("1")
        elif args.name == "mic.unmute":
            result = set_mute("0")
        elif args.name == "mic.toggle":
            result = set_mute("toggle")
        elif args.name == "mic.volume":
            result = set_volume(args.value)
        else:
            raise RuntimeError(f"unsupported audio action: {args.name}")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 7


if __name__ == "__main__":
    raise SystemExit(main())
