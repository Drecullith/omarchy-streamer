#!/usr/bin/env python3
"""Safe OBS Browser Source provisioning for Omarchy Streamer collaboration."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


class BrowserSourceError(RuntimeError):
    pass


def load_obsws():
    path = Path(__file__).with_name("obsws.py")
    spec = importlib.util.spec_from_file_location("omarchy_streamer_obsws", path)
    if not spec or not spec.loader:
        raise BrowserSourceError("could not load OBS WebSocket adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _names(rows: Any, key: str) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {str(row.get(key, "")) for row in rows if isinstance(row, dict) and row.get(key)}


def ensure_browser_source(
    url: str,
    *,
    scene_name: str,
    input_name: str,
    width: int = 1920,
    height: int = 1080,
) -> dict[str, Any]:
    if not url.startswith("https://"):
        raise BrowserSourceError("browser source URL must use https")
    if not scene_name.strip() or not input_name.strip():
        raise BrowserSourceError("scene and source names are required")
    if not (64 <= width <= 7680 and 64 <= height <= 4320):
        raise BrowserSourceError("invalid browser source dimensions")

    obs = load_obsws()
    settings = {"url": url, "width": int(width), "height": int(height)}
    created_scene = False
    created_input = False
    added_to_scene = False

    try:
        with obs.ObsClient() as client:
            scenes = client.request("GetSceneList")
            scene_names = _names(scenes.get("scenes", []), "sceneName")
            if scene_name not in scene_names:
                client.request("CreateScene", {"sceneName": scene_name})
                created_scene = True

            inputs = client.request("GetInputList")
            input_rows = inputs.get("inputs", []) if isinstance(inputs, dict) else []
            existing = None
            for row in input_rows if isinstance(input_rows, list) else []:
                if isinstance(row, dict) and str(row.get("inputName", "")) == input_name:
                    existing = row
                    break

            if existing is None:
                client.request(
                    "CreateInput",
                    {
                        "sceneName": scene_name,
                        "inputName": input_name,
                        "inputKind": "browser_source",
                        "inputSettings": settings,
                        "sceneItemEnabled": True,
                    },
                )
                created_input = True
                added_to_scene = True
            else:
                kind = str(existing.get("inputKind", ""))
                if kind and kind != "browser_source":
                    raise BrowserSourceError(
                        f"OBS input '{input_name}' already exists and is not a Browser Source"
                    )
                client.request(
                    "SetInputSettings",
                    {"inputName": input_name, "inputSettings": settings, "overlay": True},
                )
                items = client.request("GetSceneItemList", {"sceneName": scene_name})
                source_names = _names(items.get("sceneItems", []), "sourceName")
                if input_name not in source_names:
                    client.request(
                        "CreateSceneItem",
                        {"sceneName": scene_name, "sourceName": input_name, "sceneItemEnabled": True},
                    )
                    added_to_scene = True
    except BrowserSourceError:
        raise
    except Exception as exc:
        raise BrowserSourceError(str(exc)) from exc

    return {
        "ok": True,
        "sceneName": scene_name,
        "inputName": input_name,
        "createdScene": created_scene,
        "createdInput": created_input,
        "addedToScene": added_to_scene,
    }
