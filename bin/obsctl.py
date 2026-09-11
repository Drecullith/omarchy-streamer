#!/usr/bin/env python3
"""Minimal local obs-websocket v5 client for Omarchy Streamer.

Uses only Python's standard library and only connects to loopback.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import sys
import uuid


class ObsError(RuntimeError):
    pass


def _config_candidates() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("OMARCHY_STREAMER_OBS_CONFIG") or os.environ.get("OBS_WEBSOCKET_CONFIG")
    if override:
        candidates.append(Path(override).expanduser())

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidates.append(Path(xdg) / "obs-studio/plugin_config/obs-websocket/config.json")
    candidates.append(Path.home() / ".config/obs-studio/plugin_config/obs-websocket/config.json")

    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key not in seen:
            out.append(path)
            seen.add(key)
    return out


def load_connection_settings() -> tuple[str, int, str]:
    host = "127.0.0.1"
    port = 4455
    password = ""

    for path in _config_candidates():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            raw_port = data.get("server_port")
            if isinstance(raw_port, int) and 1 <= raw_port <= 65535:
                port = raw_port
            raw_password = data.get("server_password")
            if isinstance(raw_password, str):
                password = raw_password
            break

    env_port = os.environ.get("OMARCHY_STREAMER_OBS_PORT") or os.environ.get("OBS_WEBSOCKET_PORT")
    if env_port:
        try:
            parsed = int(env_port)
        except ValueError as exc:
            raise ObsError("invalid OBS WebSocket port override") from exc
        if not (1 <= parsed <= 65535):
            raise ObsError("OBS WebSocket port must be between 1 and 65535")
        port = parsed

    env_password = os.environ.get("OMARCHY_STREAMER_OBS_PASSWORD") or os.environ.get("OBS_WEBSOCKET_PASSWORD")
    if env_password is not None:
        password = env_password

    return host, port, password


def make_authentication(password: str, salt: str, challenge: str) -> str:
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode("utf-8")).digest()
    ).decode("ascii")
    return base64.b64encode(
        hashlib.sha256((secret + challenge).encode("utf-8")).digest()
    ).decode("ascii")


class WebSocket:
    def __init__(self, host: str, port: int, timeout: float = 3.0):
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ObsError("refusing non-loopback OBS WebSocket host")
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self.buffer = bytearray()

    def connect(self) -> None:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self.sock = sock

        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Sec-WebSocket-Protocol: obswebsocket.json\r\n"
            "\r\n"
        ).encode("ascii")
        sock.sendall(request)

        response = self._read_http_headers()
        first_line = response.split("\r\n", 1)[0]
        if " 101 " not in first_line:
            raise ObsError(f"OBS WebSocket upgrade failed: {first_line}")

        headers: dict[str, str] = {}
        for line in response.split("\r\n")[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()

        expected = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
            ).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise ObsError("OBS WebSocket returned an invalid handshake")

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self._send_frame(b"", opcode=0x8)
        except OSError:
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None
            self.buffer.clear()

    def _read_http_headers(self) -> str:
        if self.sock is None:
            raise ObsError("socket is not connected")
        data = bytearray(self.buffer)
        self.buffer.clear()
        while b"\r\n\r\n" not in data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ObsError("OBS WebSocket closed during handshake")
            data.extend(chunk)
            if len(data) > 65536:
                raise ObsError("OBS WebSocket handshake headers are too large")

        head, tail = data.split(b"\r\n\r\n", 1)
        self.buffer.extend(tail)
        return bytes(head).decode("iso-8859-1")

    def _recv_exact(self, length: int) -> bytes:
        if self.sock is None:
            raise ObsError("socket is not connected")
        data = bytearray()
        if self.buffer:
            take = min(length, len(self.buffer))
            data.extend(self.buffer[:take])
            del self.buffer[:take]
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise ObsError("OBS WebSocket connection closed")
            data.extend(chunk)
        return bytes(data)

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        if self.sock is None:
            raise ObsError("socket is not connected")
        first = 0x80 | (opcode & 0x0F)
        mask_key = secrets.token_bytes(4)
        length = len(payload)

        if length < 126:
            header = struct.pack("!BB", first, 0x80 | length)
        elif length <= 0xFFFF:
            header = struct.pack("!BBH", first, 0x80 | 126, length)
        else:
            header = struct.pack("!BBQ", first, 0x80 | 127, length)

        masked = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(header + mask_key + masked)

    def send_json(self, payload: dict) -> None:
        self._send_frame(
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            opcode=0x1,
        )

    def recv_text(self) -> str:
        fragments = bytearray()
        message_opcode: int | None = None

        while True:
            first, second = self._recv_exact(2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F

            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]

            mask_key = self._recv_exact(4) if masked else b""
            payload = self._recv_exact(length)
            if masked:
                payload = bytes(byte ^ mask_key[i % 4] for i, byte in enumerate(payload))

            if opcode == 0x8:
                raise ObsError("OBS WebSocket closed the connection")
            if opcode == 0x9:
                self._send_frame(payload, opcode=0xA)
                continue
            if opcode == 0xA:
                continue

            if opcode in (0x1, 0x2):
                message_opcode = opcode
                fragments = bytearray(payload)
            elif opcode == 0x0 and message_opcode is not None:
                fragments.extend(payload)
            else:
                continue

            if fin:
                if message_opcode != 0x1:
                    raise ObsError("unexpected binary OBS WebSocket message")
                return bytes(fragments).decode("utf-8")

    def recv_json(self) -> dict:
        try:
            data = json.loads(self.recv_text())
        except (UnicodeDecodeError, ValueError) as exc:
            raise ObsError("invalid JSON from OBS WebSocket") from exc
        if not isinstance(data, dict):
            raise ObsError("unexpected OBS WebSocket payload")
        return data


class ObsClient:
    def __init__(self, host: str, port: int, password: str, timeout: float = 3.0):
        self.ws = WebSocket(host, port, timeout)
        self.password = password

    def __enter__(self) -> "ObsClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.ws.close()

    def connect(self) -> None:
        self.ws.connect()
        hello = self.ws.recv_json()
        if hello.get("op") != 0:
            raise ObsError("OBS WebSocket did not send Hello")

        hello_data = hello.get("d")
        if not isinstance(hello_data, dict):
            raise ObsError("invalid OBS WebSocket Hello")

        identify: dict[str, object] = {"rpcVersion": 1, "eventSubscriptions": 0}
        authentication = hello_data.get("authentication")
        if isinstance(authentication, dict):
            challenge = authentication.get("challenge")
            salt = authentication.get("salt")
            if not isinstance(challenge, str) or not isinstance(salt, str):
                raise ObsError("invalid OBS WebSocket authentication challenge")
            if not self.password:
                raise ObsError(
                    "OBS WebSocket requires authentication but no password was found; "
                    "check Tools > WebSocket Server Settings in OBS"
                )
            identify["authentication"] = make_authentication(
                self.password, salt, challenge
            )

        self.ws.send_json({"op": 1, "d": identify})
        identified = self.ws.recv_json()
        if identified.get("op") != 2:
            raise ObsError("OBS WebSocket identification failed")

    def request(self, request_type: str, request_data: dict | None = None) -> dict:
        request_id = str(uuid.uuid4())
        payload: dict[str, object] = {
            "requestType": request_type,
            "requestId": request_id,
        }
        if request_data:
            payload["requestData"] = request_data
        self.ws.send_json({"op": 6, "d": payload})

        while True:
            message = self.ws.recv_json()
            if message.get("op") != 7:
                continue
            data = message.get("d")
            if not isinstance(data, dict) or data.get("requestId") != request_id:
                continue

            status = data.get("requestStatus")
            if not isinstance(status, dict):
                raise ObsError(f"{request_type} returned no request status")
            if not status.get("result"):
                code = status.get("code", "?")
                comment = status.get("comment", "request failed")
                raise ObsError(f"{request_type} failed ({code}): {comment}")

            response = data.get("responseData")
            return response if isinstance(response, dict) else {}


def status_payload(client: ObsClient) -> dict:
    version = client.request("GetVersion")
    stream = client.request("GetStreamStatus")
    record = client.request("GetRecordStatus")

    replay_active = None
    try:
        replay = client.request("GetReplayBufferStatus")
        replay_active = bool(replay.get("outputActive"))
    except ObsError:
        pass

    # GetSceneList includes currentProgramSceneName, avoiding a separate
    # GetCurrentProgramScene call.
    scenes = client.request("GetSceneList")
    scene_names = [
        entry["sceneName"]
        for entry in scenes.get("scenes", [])
        if isinstance(entry, dict) and isinstance(entry.get("sceneName"), str)
    ]

    return {
        "ok": True,
        "connected": True,
        "obsStudioVersion": version.get("obsVersion"),
        "obsWebSocketVersion": version.get("obsWebSocketVersion"),
        "streamActive": bool(stream.get("outputActive")),
        "recordActive": bool(record.get("outputActive")),
        "replayBufferActive": replay_active,
        "currentProgramSceneName": scenes.get("currentProgramSceneName"),
        "scenes": scene_names,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local OBS WebSocket v5 control client")
    parser.add_argument("--timeout", type=float, default=3.0, help="socket timeout in seconds")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="read stream, recording, replay-buffer and scene status")

    req = sub.add_parser("request", help="send one OBS WebSocket request")
    req.add_argument("request_type")
    req.add_argument("request_data_json", nargs="?")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    try:
        host, port, password = load_connection_settings()

        if args.command == "status":
            with ObsClient(host, port, password, args.timeout) as client:
                print(json.dumps(status_payload(client), separators=(",", ":")))
            return 0

        request_data = None
        if args.request_data_json:
            try:
                request_data = json.loads(args.request_data_json)
            except ValueError as exc:
                raise ObsError("request data must be valid JSON") from exc
            if not isinstance(request_data, dict):
                raise ObsError("request data must be a JSON object")

        with ObsClient(host, port, password, args.timeout) as client:
            response = client.request(args.request_type, request_data)
        print(json.dumps({
            "ok": True,
            "requestType": args.request_type,
            "responseData": response,
        }, separators=(",", ":")))
        return 0

    except (ObsError, OSError, socket.timeout) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
