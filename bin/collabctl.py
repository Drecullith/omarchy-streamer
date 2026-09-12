#!/usr/bin/env python3
"""Collaboration controller for Omarchy Streamer.

VDO.Ninja is the first provider. Room credentials, managed guest stream IDs,
and page-control IDs remain in the user's local state and are intentionally
excluded from normal status output.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

PROVIDER_ID = "vdo.ninja"
PROVIDER_LABEL = "VDO.Ninja"
BASE_URL = "https://vdo.ninja/"
DEFAULT_SLOT_COUNT = 4
DEFAULT_OBS_SCENE = os.environ.get("OMARCHY_STREAMER_GUEST_SCENE", "Omarchy Guests")
GUEST_STATE_MAX_AGE = int(os.environ.get("OMARCHY_STREAMER_GUEST_STATE_MAX_AGE", "30"))
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
SESSION_FILE = STATE_ROOT / "collab-session.json"
GUEST_STATE_FILE = STATE_ROOT / "collab-guest-state.json"
_GUEST_STATE_LOCK = threading.Lock()


class CollabError(RuntimeError):
    pass


def ensure_state_dir() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        STATE_ROOT.chmod(0o700)
    except OSError:
        pass


def secure_write_json(path: Path, value: Any) -> None:
    ensure_state_dir()
    temp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(value, separators=(",", ":")) + "\n"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def new_slot(number: int) -> dict[str, Any]:
    return {
        "slot": int(number),
        "label": f"Guest {number}",
        "streamId": "os_guest_" + secrets.token_hex(8),
        "controlId": secrets.token_hex(18),
    }


def normalize_slots(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        try:
            number = int(raw.get("slot", 0))
        except (TypeError, ValueError):
            continue
        label = str(raw.get("label", f"Guest {number}"))[:80]
        stream_id = str(raw.get("streamId", ""))
        control_id = str(raw.get("controlId", ""))
        if number < 1 or not stream_id or not control_id:
            continue
        out.append({"slot": number, "label": label or f"Guest {number}", "streamId": stream_id, "controlId": control_id})
    return sorted(out, key=lambda item: int(item["slot"]))


def validate_session(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CollabError("invalid collaboration session")
    provider = str(value.get("provider", ""))
    room = str(value.get("room", ""))
    password = str(value.get("password", ""))
    if provider != PROVIDER_ID or not room or not password:
        raise CollabError("invalid collaboration session")
    value = dict(value)
    value["slots"] = normalize_slots(value.get("slots", []))
    return value


def save_session(session: dict[str, Any]) -> None:
    secure_write_json(SESSION_FILE, session)


def load_session() -> dict[str, Any] | None:
    if not SESSION_FILE.is_file():
        return None
    try:
        session = validate_session(json.loads(SESSION_FILE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollabError(f"could not read collaboration session: {exc}") from exc

    if not session["slots"]:
        session["version"] = 2
        session["slots"] = [new_slot(i) for i in range(1, DEFAULT_SLOT_COUNT + 1)]
        save_session(session)
    return session


def create_session(force: bool = False) -> dict[str, Any]:
    if not force:
        current = load_session()
        if current is not None:
            return current
    session = {
        "version": 2,
        "provider": PROVIDER_ID,
        "room": "omarchy_" + secrets.token_hex(8),
        "password": secrets.token_urlsafe(24),
        "createdAt": int(time.time()),
        "slots": [new_slot(i) for i in range(1, DEFAULT_SLOT_COUNT + 1)],
    }
    save_session(session)
    clear_guest_state()
    return session


def require_session() -> dict[str, Any]:
    session = load_session()
    if session is None:
        raise CollabError("no collaboration room exists; create one first")
    return session


def get_slot(session: dict[str, Any], raw: str | int) -> dict[str, Any]:
    try:
        number = int(raw)
    except (TypeError, ValueError) as exc:
        raise CollabError("guest slot must be a number") from exc
    for slot in session.get("slots", []):
        if int(slot.get("slot", 0)) == number:
            return slot
    raise CollabError(f"guest slot {number} does not exist")


def provider_url(session: dict[str, Any], kind: str) -> str:
    room = session["room"]
    password = session["password"]
    if kind == "director":
        query = urlencode({"director": room, "password": password}) + "&cleanish"
    elif kind == "guest":
        query = urlencode({"room": room, "password": password}) + "&autostart"
    elif kind == "program":
        query = urlencode({"scene": "0", "room": room, "password": password}) + "&cleanoutput"
    else:
        raise CollabError(f"unsupported collaboration URL kind: {kind}")
    return BASE_URL + "?" + query


def slot_url(session: dict[str, Any], slot: dict[str, Any], kind: str) -> str:
    base = {"room": session["room"], "password": session["password"]}
    if kind == "guest":
        base.update({"push": slot["streamId"], "label": slot["label"], "api": slot["controlId"]})
        return BASE_URL + "?" + urlencode(base) + "&autostart"
    if kind == "solo":
        base.update({"scene": "0", "view": slot["streamId"]})
        return BASE_URL + "?" + urlencode(base) + "&cleanoutput"
    raise CollabError(f"unsupported guest slot URL kind: {kind}")


def copy_url(url: str) -> None:
    wl_copy = shutil.which("wl-copy")
    if not wl_copy:
        raise CollabError("wl-copy is required to copy collaboration links")
    try:
        subprocess.run([wl_copy], input=url, text=True, check=True, timeout=3)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CollabError(f"could not copy collaboration link: {exc}") from exc


def open_director() -> None:
    opener = shutil.which("xdg-open")
    if not opener:
        raise CollabError("xdg-open is required to open the collaboration director")
    url = provider_url(require_session(), "director")
    try:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as exc:
        raise CollabError(f"could not open collaboration director: {exc}") from exc


def load_guest_state() -> list[dict[str, Any]]:
    if not GUEST_STATE_FILE.is_file():
        return []
    try:
        value = json.loads(GUEST_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        try:
            slot = int(raw.get("slot", 0))
            checked_at = int(raw.get("checkedAt", 0))
        except (TypeError, ValueError):
            continue
        if slot < 1:
            continue
        online = raw.get("online") if isinstance(raw.get("online"), bool) else None
        mic_enabled = raw.get("micEnabled") if isinstance(raw.get("micEnabled"), bool) else None
        error = str(raw.get("error", ""))[:32]
        out.append({"slot": slot, "online": online, "micEnabled": mic_enabled, "checkedAt": checked_at, "error": error})
    return out


def save_guest_state(states: list[dict[str, Any]]) -> None:
    secure_write_json(GUEST_STATE_FILE, states)


def clear_guest_state(slot_number: int | None = None) -> None:
    if slot_number is None:
        try:
            GUEST_STATE_FILE.unlink()
        except FileNotFoundError:
            pass
        return
    with _GUEST_STATE_LOCK:
        remaining = [entry for entry in load_guest_state() if int(entry.get("slot", 0)) != int(slot_number)]
        if remaining:
            save_guest_state(remaining)
        else:
            try:
                GUEST_STATE_FILE.unlink()
            except FileNotFoundError:
                pass


def update_guest_state(slot_number: int, *, online: bool | None, mic_enabled: bool | None = None, error: str = "") -> dict[str, Any]:
    with _GUEST_STATE_LOCK:
        states = {int(entry["slot"]): dict(entry) for entry in load_guest_state()}
        previous = states.get(int(slot_number), {})
        if mic_enabled is None and online is True:
            previous_mic = previous.get("micEnabled")
            mic_enabled = previous_mic if isinstance(previous_mic, bool) else None
        entry = {
            "slot": int(slot_number),
            "online": online,
            "micEnabled": mic_enabled if online is True else None,
            "checkedAt": int(time.time()),
            "error": str(error)[:32],
        }
        states[int(slot_number)] = entry
        save_guest_state([states[key] for key in sorted(states)])
        return entry


def safe_guest_states(session: dict[str, Any] | None) -> list[dict[str, Any]]:
    if session is None:
        return []
    cached = {int(entry["slot"]): entry for entry in load_guest_state()}
    now = int(time.time())
    result: list[dict[str, Any]] = []
    for slot in session.get("slots", []):
        number = int(slot["slot"])
        entry = cached.get(number)
        if not entry:
            result.append({"slot": number, "online": None, "micEnabled": None, "checkedAt": 0, "stale": True, "error": ""})
            continue
        checked_at = int(entry.get("checkedAt", 0))
        result.append({
            "slot": number,
            "online": entry.get("online") if isinstance(entry.get("online"), bool) else None,
            "micEnabled": entry.get("micEnabled") if isinstance(entry.get("micEnabled"), bool) else None,
            "checkedAt": checked_at,
            "stale": checked_at <= 0 or now - checked_at > GUEST_STATE_MAX_AGE,
            "error": str(entry.get("error", ""))[:32],
        })
    return result


def load_vdoapi():
    path = Path(__file__).with_name("vdoapi.py")
    spec = importlib.util.spec_from_file_location("omarchy_streamer_vdoapi", path)
    if not spec or not spec.loader:
        raise CollabError("could not load VDO.Ninja control adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def probe_slot(slot: dict[str, Any]) -> dict[str, Any]:
    adapter = load_vdoapi()
    number = int(slot["slot"])
    try:
        adapter.probe(slot["controlId"])
        return update_guest_state(number, online=True, error="")
    except adapter.VdoApiTimeout:
        return update_guest_state(number, online=False, mic_enabled=None, error="timeout")
    except adapter.VdoApiError:
        return update_guest_state(number, online=None, mic_enabled=None, error="connection")


def refresh_guests() -> list[dict[str, Any]]:
    session = require_session()
    slots = list(session.get("slots", []))
    if not slots:
        return []
    # Probe concurrently, but update_guest_state serializes each atomic
    # read-modify-write so parallel callbacks cannot clobber another slot.
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(slots))) as pool:
        list(pool.map(probe_slot, slots))
    return safe_guest_states(session)


def set_guest_mic(raw: str, enabled: bool) -> dict[str, Any]:
    session = require_session()
    slot = get_slot(session, raw)
    adapter = load_vdoapi()
    try:
        result = adapter.set_mic(slot["controlId"], enabled)
    except adapter.VdoApiTimeout as exc:
        update_guest_state(int(slot["slot"]), online=False, mic_enabled=None, error="timeout")
        raise CollabError("guest page did not answer the microphone command") from exc
    except adapter.VdoApiError as exc:
        update_guest_state(int(slot["slot"]), online=None, mic_enabled=None, error="connection")
        raise CollabError("guest control connection failed") from exc
    mic_enabled = result if isinstance(result, bool) else None
    state = update_guest_state(int(slot["slot"]), online=True, mic_enabled=mic_enabled, error="")
    return {"slot": int(slot["slot"]), "online": True, "micEnabled": state["micEnabled"]}


def disconnect_guest(raw: str) -> dict[str, Any]:
    session = require_session()
    slot = get_slot(session, raw)
    adapter = load_vdoapi()
    try:
        adapter.hangup(slot["controlId"])
    except adapter.VdoApiTimeout as exc:
        raise CollabError("guest page did not answer the disconnect command") from exc
    except adapter.VdoApiError as exc:
        raise CollabError("guest control connection failed") from exc
    update_guest_state(int(slot["slot"]), online=False, mic_enabled=None, error="")
    return {"slot": int(slot["slot"]), "online": False, "micEnabled": None}


def rotate_slot(raw: str) -> int:
    session = require_session()
    old = get_slot(session, raw)
    number = int(old["slot"])
    session["slots"] = [new_slot(number) if int(slot["slot"]) == number else slot for slot in session["slots"]]
    save_session(session)
    clear_guest_state(number)
    return number


def reset_session() -> None:
    try:
        SESSION_FILE.unlink()
    except FileNotFoundError:
        pass
    clear_guest_state()


def load_obsbrowser():
    path = Path(__file__).with_name("obsbrowser.py")
    spec = importlib.util.spec_from_file_location("omarchy_streamer_obsbrowser", path)
    if not spec or not spec.loader:
        raise CollabError("could not load OBS Browser Source adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_program_to_obs(slot_number: str | None = None) -> dict[str, Any]:
    session = require_session()
    if slot_number is None:
        url = provider_url(session, "program")
        input_name = "Omarchy Streamer - Guests"
    else:
        slot = get_slot(session, slot_number)
        url = slot_url(session, slot, "solo")
        input_name = f"Omarchy Streamer - Guest {slot['slot']}"
    try:
        adapter = load_obsbrowser()
        return adapter.ensure_browser_source(url, scene_name=DEFAULT_OBS_SCENE, input_name=input_name)
    except Exception as exc:
        raise CollabError(f"could not add collaboration source to OBS: {exc}") from exc


def status() -> dict[str, Any]:
    error = ""
    try:
        session = load_session()
    except CollabError as exc:
        session = None
        error = str(exc)
    slots = session.get("slots", []) if session else []
    return {
        "ready": True,
        "active": session is not None,
        "provider": PROVIDER_ID,
        "providerLabel": PROVIDER_LABEL,
        "clipboardReady": shutil.which("wl-copy") is not None,
        "browserReady": shutil.which("xdg-open") is not None,
        "inviteReady": session is not None,
        "programUrlReady": session is not None,
        "managedSlotsReady": bool(slots),
        "guestControlReady": bool(slots),
        "slotCount": len(slots),
        "guests": safe_guest_states(session),
        "obsSceneName": DEFAULT_OBS_SCENE,
        "credentialsExposed": False,
        "error": error,
    }


def perform(action: str, value: str = "") -> dict[str, Any]:
    details: dict[str, Any] = {}
    if action == "collab.create":
        create_session(force=False)
    elif action == "collab.rotate":
        create_session(force=True)
    elif action == "collab.reset":
        reset_session()
    elif action == "collab.open-director":
        open_director()
    elif action == "collab.copy-invite":
        copy_url(provider_url(require_session(), "guest"))
    elif action == "collab.copy-program":
        copy_url(provider_url(require_session(), "program"))
    elif action == "collab.slot-rotate":
        details["slot"] = rotate_slot(value)
    elif action == "collab.copy-slot-invite":
        session = require_session()
        slot = get_slot(session, value)
        copy_url(slot_url(session, slot, "guest"))
        details["slot"] = int(slot["slot"])
    elif action == "collab.copy-slot-source":
        session = require_session()
        slot = get_slot(session, value)
        copy_url(slot_url(session, slot, "solo"))
        details["slot"] = int(slot["slot"])
    elif action == "collab.obs-add-program":
        details.update(add_program_to_obs(None))
    elif action == "collab.obs-add-slot":
        details.update(add_program_to_obs(value))
        details["slot"] = int(value)
    elif action == "collab.guest-refresh":
        details["guests"] = refresh_guests()
    elif action == "collab.guest-mute":
        details.update(set_guest_mic(value, False))
    elif action == "collab.guest-unmute":
        details.update(set_guest_mic(value, True))
    elif action == "collab.guest-disconnect":
        details.update(disconnect_guest(value))
    else:
        raise CollabError(f"unsupported collaboration action: {action}")
    return {"ok": True, "action": action, "provider": PROVIDER_ID, **details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer collaboration controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    action.add_argument("value", nargs="?", default="")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print(json.dumps(status(), separators=(",", ":")))
        else:
            print(json.dumps(perform(args.name, args.value), separators=(",", ":")))
        return 0
    except CollabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
