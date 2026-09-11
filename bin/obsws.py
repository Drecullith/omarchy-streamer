#!/usr/bin/env python3
"""Tiny OBS WebSocket v5 client for Omarchy Streamer.

Uses only Python's standard library. By default it connects only to localhost
and reads OBS's own obs-websocket config for port/password, so credentials do
not live in this repository or Omarchy Streamer's state.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import uuid
from pathlib import Path
from typing import Any

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4455
DEFAULT_TIMEOUT = float(os.environ.get("OMARCHY_STREAMER_OBS_TIMEOUT", "0.8"))


class ObsError(RuntimeError):
    pass


class ObsRequestError(ObsError):
    def __init__(self, request_type: str, code: int, comment: str = "") -> None:
        self.request_type = request_type
        self.code = code
        self.comment = comment
        message = f"{request_type} failed ({code})"
        if comment:
            message += f": {comment}"
        super().__init__(message)


def obs_config_path() -> Path:
    override = os.environ.get("OMARCHY_STREAMER_OBS_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return xdg / "obs-studio" / "plugin_config" / "obs-websocket" / "config.json"


def load_connection() -> tuple[str, int, str]:
    host = os.environ.get("OMARCHY_STREAMER_OBS_HOST", DEFAULT_HOST)
    allow_remote = os.environ.get("OMARCHY_STREAMER_OBS_ALLOW_REMOTE", "0") == "1"
    if host not in {"127.0.0.1", "localhost", "::1"} and not allow_remote:
        raise ObsError("remote OBS hosts are disabled unless OMARCHY_STREAMER_OBS_ALLOW_REMOTE=1")

    cfg: dict[str, Any] = {}
    path = obs_config_path()
    try:
        cfg = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError) as exc:
        raise ObsError(f"could not read OBS WebSocket config: {exc}") from exc

    port_raw = os.environ.get("OMARCHY_STREAMER_OBS_PORT", cfg.get("server_port", DEFAULT_PORT))
    try:
        port = int(port_raw)
    except (TypeError, ValueError) as exc:
        raise ObsError("invalid OBS WebSocket port") from exc
    if not (1 <= port <= 65535):
        raise ObsError("invalid OBS WebSocket port")

    password = os.environ.get("OMARCHY_STREAMER_OBS_PASSWORD", str(cfg.get("server_password", "")))
    return host, port, password


class WebSocket:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buffer = bytearray()

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        sock.sendall(request)

        raw = bytearray()
        marker = b"\r\n\r\n"
        while marker not in raw:
            chunk = sock.recv(4096)
            if not chunk:
                raise ObsError("OBS closed the WebSocket handshake")
            raw.extend(chunk)
            if len(raw) > 65536:
                raise ObsError("oversized WebSocket handshake")

        header_bytes, remainder = bytes(raw).split(marker, 1)
        headers = header_bytes.decode("latin1")
        lines = headers.split("\r\n")
        if not lines or " 101 " not in f" {lines[0]} ":
            raise ObsError(f"OBS WebSocket handshake failed: {lines[0] if lines else 'no response'}")

        values: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            values[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        if values.get("sec-websocket-accept") != expected:
            raise ObsError("invalid WebSocket handshake response")

        self.sock = sock
        self.buffer = bytearray(remainder)

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self._send_frame(b"", opcode=0x8)
        except (OSError, ObsError):
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None
            self.buffer.clear()

    def _read_exact(self, count: int) -> bytes:
        if self.sock is None:
            raise ObsError("WebSocket is not connected")
        out = bytearray()
        if self.buffer:
            take = min(count, len(self.buffer))
            out.extend(self.buffer[:take])
            del self.buffer[:take]
        while len(out) < count:
            chunk = self.sock.recv(count - len(out))
            if not chunk:
                raise ObsError("OBS closed the WebSocket connection")
            out.extend(chunk)
        return bytes(out)

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        if self.sock is None:
            raise ObsError("WebSocket is not connected")
        first = 0x80 | (opcode & 0x0F)
        mask_key = os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes((first, 0x80 | length))
        elif length <= 0xFFFF:
            header = bytes((first, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((first, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(header + mask_key + masked)

    def send_json(self, value: dict[str, Any]) -> None:
        self._send_frame(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def recv_json(self) -> dict[str, Any]:
        fragments = bytearray()
        text_started = False
        while True:
            head = self._read_exact(2)
            first, second = head[0], head[1]
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask_key = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))

            if opcode == 0x8:
                raise ObsError("OBS closed the WebSocket connection")
            if opcode == 0x9:
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                fragments = bytearray(payload)
                text_started = True
            elif opcode == 0x0 and text_started:
                fragments.extend(payload)
            else:
                continue

            if fin:
                try:
                    value = json.loads(fragments.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ObsError("OBS sent invalid JSON") from exc
                if not isinstance(value, dict):
                    raise ObsError("OBS sent a non-object JSON message")
                return value


class ObsClient:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT) -> None:
        host, port, password = load_connection()
        self.password = password
        self.ws = WebSocket(host, port, timeout)

    def __enter__(self) -> "ObsClient":
        self.ws.connect()
        hello = self.ws.recv_json()
        if hello.get("op") != 0:
            raise ObsError("OBS did not send protocol Hello")
        data = hello.get("d") or {}
        identify: dict[str, Any] = {"rpcVersion": 1, "eventSubscriptions": 0}
        auth = data.get("authentication")
        if auth:
            if not self.password:
                raise ObsError("OBS WebSocket authentication is enabled but no password was found")
            salt = str(auth.get("salt", ""))
            challenge = str(auth.get("challenge", ""))
            secret = base64.b64encode(hashlib.sha256((self.password + salt).encode()).digest()).decode()
            response = base64.b64encode(hashlib.sha256((secret + challenge).encode()).digest()).decode()
            identify["authentication"] = response
        self.ws.send_json({"op": 1, "d": identify})
        identified = self.ws.recv_json()
        if identified.get("op") != 2:
            raise ObsError("OBS WebSocket authentication/identification failed")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.ws.close()

    def request(self, request_type: str, request_data: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        data: dict[str, Any] = {"requestType": request_type, "requestId": request_id}
        if request_data:
            data["requestData"] = request_data
        self.ws.send_json({"op": 6, "d": data})
        while True:
            message = self.ws.recv_json()
            if message.get("op") != 7:
                continue
            response = message.get("d") or {}
            if response.get("requestId") != request_id:
                continue
            status = response.get("requestStatus") or {}
            if not status.get("result", False):
                raise ObsRequestError(request_type, int(status.get("code", 0)), str(status.get("comment", "")))
            value = response.get("responseData")
            return value if isinstance(value, dict) else {}


def safe_request(client: ObsClient, request_type: str, request_data: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str]:
    try:
        return client.request(request_type, request_data), ""
    except ObsRequestError as exc:
        return None, str(exc)


def status() -> dict[str, Any]:
    result: dict[str, Any] = {
        "connected": False,
        "streaming": None,
        "recording": None,
        "replayBuffer": None,
        "currentScene": "",
        "error": "",
    }
    try:
        with ObsClient() as client:
            result["connected"] = True
            stream, stream_error = safe_request(client, "GetStreamStatus")
            record, record_error = safe_request(client, "GetRecordStatus")
            replay, replay_error = safe_request(client, "GetReplayBufferStatus")
            scenes, scene_error = safe_request(client, "GetSceneList")
            if stream is not None:
                result["streaming"] = bool(stream.get("outputActive", False))
            if record is not None:
                result["recording"] = bool(record.get("outputActive", False))
            if replay is not None:
                result["replayBuffer"] = bool(replay.get("outputActive", False))
            if scenes is not None:
                result["currentScene"] = str(scenes.get("currentProgramSceneName", ""))
            errors = [e for e in (stream_error, record_error, replay_error, scene_error) if e]
            result["error"] = "; ".join(errors)
    except (ObsError, OSError, socket.timeout) as exc:
        result["error"] = str(exc)
    return result


def perform(command: str, value: str = "") -> dict[str, Any]:
    mapping: dict[str, tuple[str, dict[str, Any] | None]] = {
        "stream.start": ("StartStream", None),
        "stream.stop": ("StopStream", None),
        "record.start": ("StartRecord", None),
        "record.stop": ("StopRecord", None),
        "clip.save": ("SaveReplayBuffer", None),
        "replay.start": ("StartReplayBuffer", None),
        "replay.stop": ("StopReplayBuffer", None),
    }
    if command == "scene.set":
        if not value:
            raise ObsError("scene.set requires a scene name")
        request_type, data = "SetCurrentProgramScene", {"sceneName": value}
    elif command in mapping:
        request_type, data = mapping[command]
    else:
        raise ObsError(f"unsupported OBS action: {command}")

    with ObsClient() as client:
        response = client.request(request_type, data)
    return {"ok": True, "action": command, "response": response}


def main() -> int:
    parser = argparse.ArgumentParser(description="Omarchy Streamer OBS WebSocket adapter")
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
        print(json.dumps(perform(args.name, args.value), separators=(",", ":")))
        return 0
    except (ObsError, OSError, socket.timeout) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    raise SystemExit(main())
