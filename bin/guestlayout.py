#!/usr/bin/env python3
"""Deterministic OBS layout helpers for Omarchy Streamer managed guests."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_SCENE = os.environ.get("OMARCHY_STREAMER_GUEST_SCENE", "Omarchy Guests")
PREFIX = "Omarchy Streamer - Guest "


class LayoutError(RuntimeError):
    pass


def load_obsws():
    path = Path(__file__).with_name("obsws.py")
    spec = importlib.util.spec_from_file_location("omarchy_streamer_obsws", path)
    if not spec or not spec.loader:
        raise LayoutError("could not load OBS WebSocket adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_slot(name: str) -> int | None:
    if not name.startswith(PREFIX):
        return None
    try:
        value = int(name[len(PREFIX):])
    except ValueError:
        return None
    return value if 1 <= value <= 32 else None


def boxes(preset: str, slots: list[int], width: int, height: int) -> dict[int, tuple[float, float, float, float]]:
    if not slots:
        raise LayoutError("no managed guest sources exist in the OBS guest scene")
    preset = preset.strip().lower()
    if preset == "auto":
        preset = "single" if len(slots) == 1 else ("split" if len(slots) == 2 else "grid")

    if preset == "single":
        slot = slots[0]
        return {slot: (0, 0, width, height)}

    if preset == "split":
        if len(slots) < 2:
            return {slots[0]: (0, 0, width, height)}
        half = width / 2
        return {
            slots[0]: (0, 0, half, height),
            slots[1]: (half, 0, half, height),
        }

    if preset == "grid":
        if len(slots) == 1:
            return {slots[0]: (0, 0, width, height)}
        if len(slots) == 2:
            return boxes("split", slots, width, height)
        half_w, half_h = width / 2, height / 2
        positions = [(0, 0), (half_w, 0), (0, half_h), (half_w, half_h)]
        return {slot: (*positions[i], half_w, half_h) for i, slot in enumerate(slots[:4])}

    if preset.startswith("focus:"):
        try:
            focus = int(preset.split(":", 1)[1])
        except ValueError as exc:
            raise LayoutError("focus layout requires a guest slot number") from exc
        if focus not in slots:
            raise LayoutError(f"managed Guest {focus} is not present in the OBS guest scene")
        others = [slot for slot in slots if slot != focus][:3]
        main_w = width * 0.75 if others else width
        result = {focus: (0, 0, main_w, height)}
        if others:
            cell_h = height / len(others)
            for i, slot in enumerate(others):
                result[slot] = (main_w, i * cell_h, width - main_w, cell_h)
        return result

    raise LayoutError("layout must be auto, single, split, grid, or focus:<slot>")


def transform_for(box: tuple[float, float, float, float]) -> dict[str, Any]:
    x, y, w, h = box
    return {
        "positionX": float(x),
        "positionY": float(y),
        "rotation": 0.0,
        "scaleX": 1.0,
        "scaleY": 1.0,
        "alignment": 5,
        "boundsType": "OBS_BOUNDS_SCALE_INNER",
        "boundsAlignment": 0,
        "boundsWidth": float(max(1, w)),
        "boundsHeight": float(max(1, h)),
        "cropLeft": 0,
        "cropRight": 0,
        "cropTop": 0,
        "cropBottom": 0,
    }


def apply_layout(preset: str, scene_name: str = DEFAULT_SCENE) -> dict[str, Any]:
    obs = load_obsws()
    try:
        with obs.ObsClient() as client:
            items_raw = client.request("GetSceneItemList", {"sceneName": scene_name})
            rows = items_raw.get("sceneItems", []) if isinstance(items_raw, dict) else []
            items: dict[int, int] = {}
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                slot = parse_slot(str(row.get("sourceName", "")))
                item_id = row.get("sceneItemId")
                if slot is not None and isinstance(item_id, int):
                    items[slot] = item_id
            slots = sorted(items)
            video = client.request("GetVideoSettings")
            width = int(video.get("baseWidth", 1920)) if isinstance(video, dict) else 1920
            height = int(video.get("baseHeight", 1080)) if isinstance(video, dict) else 1080
            layout = boxes(preset, slots, width, height)
            for slot in slots:
                enabled = slot in layout
                client.request("SetSceneItemEnabled", {
                    "sceneName": scene_name,
                    "sceneItemId": items[slot],
                    "sceneItemEnabled": enabled,
                })
                if enabled:
                    client.request("SetSceneItemTransform", {
                        "sceneName": scene_name,
                        "sceneItemId": items[slot],
                        "sceneItemTransform": transform_for(layout[slot]),
                    })
    except LayoutError:
        raise
    except Exception as exc:
        raise LayoutError(str(exc)) from exc

    return {
        "ok": True,
        "action": "collab.layout",
        "preset": preset,
        "sceneName": scene_name,
        "managedGuests": slots,
        "visibleGuests": sorted(layout),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer guest layout controller")
    parser.add_argument("preset")
    args = parser.parse_args()
    try:
        print(json.dumps(apply_layout(args.preset), separators=(",", ":")))
        return 0
    except LayoutError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
