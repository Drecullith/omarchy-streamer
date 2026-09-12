#!/usr/bin/env python3
"""Collaboration room controller for Omarchy Streamer.

The first provider adapter uses VDO.Ninja. Session credentials stay in the
user's local state directory and are never included in normal status output.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

PROVIDER_ID = "vdo.ninja"
PROVIDER_LABEL = "VDO.Ninja"
BASE_URL = "https://vdo.ninja/"
STATE_ROOT = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "omarchy-streamer"
SESSION_FILE = STATE_ROOT / "collab-session.json"


class CollabError(RuntimeError):
    pass


def ensure_state_dir() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        STATE_ROOT.chmod(0o700)
    except OSError:
        pass


def validate_session(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CollabError("invalid collaboration session")
    provider = str(value.get("provider", ""))
    room = str(value.get("room", ""))
    password = str(value.get("password", ""))
    if provider != PROVIDER_ID or not room or not password:
        raise CollabError("invalid collaboration session")
    return value


def load_session() -> dict[str, Any] | None:
    if not SESSION_FILE.is_file():
        return None
    try:
        return validate_session(json.loads(SESSION_FILE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise CollabError(f"could not read collaboration session: {exc}") from exc


def save_session(session: dict[str, Any]) -> None:
    ensure_state_dir()
    temp = SESSION_FILE.with_suffix(".tmp")
    payload = json.dumps(session, separators=(",", ":")) + "\n"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, SESSION_FILE)
        os.chmod(SESSION_FILE, 0o600)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def create_session(force: bool = False) -> dict[str, Any]:
    if not force:
        current = load_session()
        if current is not None:
            return current
    session = {
        "version": 1,
        "provider": PROVIDER_ID,
        "room": "omarchy-" + secrets.token_hex(8),
        "password": secrets.token_urlsafe(24),
        "createdAt": int(time.time()),
    }
    save_session(session)
    return session


def require_session() -> dict[str, Any]:
    session = load_session()
    if session is None:
        raise CollabError("no collaboration room exists; create one first")
    return session


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


def copy_secret_url(kind: str) -> None:
    wl_copy = shutil.which("wl-copy")
    if not wl_copy:
        raise CollabError("wl-copy is required to copy collaboration links")
    url = provider_url(require_session(), kind)
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
        subprocess.Popen(
            [opener, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise CollabError(f"could not open collaboration director: {exc}") from exc


def reset_session() -> None:
    try:
        SESSION_FILE.unlink()
    except FileNotFoundError:
        pass


def status() -> dict[str, Any]:
    error = ""
    try:
        session = load_session()
    except CollabError as exc:
        session = None
        error = str(exc)
    return {
        "ready": True,
        "active": session is not None,
        "provider": PROVIDER_ID,
        "providerLabel": PROVIDER_LABEL,
        "clipboardReady": shutil.which("wl-copy") is not None,
        "browserReady": shutil.which("xdg-open") is not None,
        "inviteReady": session is not None,
        "programUrlReady": session is not None,
        "credentialsExposed": False,
        "error": error,
    }


def perform(action: str) -> dict[str, Any]:
    if action == "collab.create":
        create_session(force=False)
    elif action == "collab.rotate":
        create_session(force=True)
    elif action == "collab.reset":
        reset_session()
    elif action == "collab.open-director":
        open_director()
    elif action == "collab.copy-invite":
        copy_secret_url("guest")
    elif action == "collab.copy-program":
        copy_secret_url("program")
    else:
        raise CollabError(f"unsupported collaboration action: {action}")
    return {"ok": True, "action": action, "provider": PROVIDER_ID}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer collaboration controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    action = sub.add_parser("action")
    action.add_argument("name")
    args = parser.parse_args()

    try:
        if args.command == "status":
            print(json.dumps(status(), separators=(",", ":")))
        else:
            print(json.dumps(perform(args.name), separators=(",", ":")))
        return 0
    except CollabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
