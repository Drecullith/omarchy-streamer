#!/usr/bin/env python3
"""Minimal VDO.Ninja page-control client for Omarchy Streamer.

This module speaks the documented private ``&api`` WebSocket control channel.
It intentionally accepts a control ID only as a Python argument so callers can
keep that capability out of process command lines and generic status output.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
import uuid
from typing import Any
from urllib.parse import urlparse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
DEFAULT_ENDPOINT = os.environ.get("OMARCHY_STREAMER_VDO_API_URL", "wss://api.vdo.ninja/")
DEFAULT_TIMEOUT = float(os.environ.get("OMARCHY_STREAMER_VDO_API_TIMEOUT", "1.4"))
_MISSING = object()


class VdoApiError(RuntimeError):
    pass


class VdoApiTimeout(VdoApiError):
    pass


class WebSocket:
    def __init__(self, endpoint: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
            raise VdoApiError("VDO API endpoint must use ws:// or wss://")
        self.secure = parsed.scheme == "wss"
        self.host = parsed.hostname
        self.port = parsed.port or (443 if self.secure else 80)
        self.path = parsed.path or "/"
        if parsed.query:
            self.path += "?" + parsed.query
        self.timeout = timeout
        self.sock: socket.socket | ssl.SSLSocket | None = None
        self.buffer = bytearray()

    def connect(self) -> None:
        raw = socket.create_connection((self.host, self.port), timeout=self.timeout)
        raw.settimeout(self.timeout)
        if self.secure:
            context = ssl.create_default_context()
            sock: socket.socket | ssl.SSLSocket = context.wrap_socket(raw, server_hostname=self.host)
        else:
            sock = raw
        sock.settimeout(self.timeout)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = self.host
        if (self.secure and self.port != 443) or (not self.secure and self.port != 80):
            host_header += f":{self.port}"
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {host_header}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode("ascii")
        sock.sendall(request)

        raw_headers = bytearray()
        marker = b"\r\n\r\n"
        while marker not in raw_headers:
            chunk = sock.recv(4096)
            if not chunk:
                raise VdoApiError("VDO API closed the WebSocket handshake")
            raw_headers.extend(chunk)
            if len(raw_headers) > 65536:
                raise VdoApiError("oversized VDO API WebSocket handshake")

        header_bytes, remainder = bytes(raw_headers).split(marker, 1)
        lines = header_bytes.decode("latin1").split("\r\n")
        if not lines or " 101 " not in f" {lines[0]} ":
            raise VdoApiError(f"VDO API WebSocket handshake failed: {lines[0] if lines else 'no response'}")
        values: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            values[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        if values.get("sec-websocket-accept") != expected:
            raise VdoApiError("invalid VDO API WebSocket handshake response")

        self.sock = sock
        self.buffer = bytearray(remainder)

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self._send_frame(b"", opcode=0x8)
        except (OSError, VdoApiError):
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None
            self.buffer.clear()

    def __enter__(self) -> "WebSocket":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _read_exact(self, count: int) -> bytes:
        if self.sock is None:
            raise VdoApiError("VDO API WebSocket is not connected")
        out = bytearray()
        if self.buffer:
            take = min(count, len(self.buffer))
            out.extend(self.buffer[:take])
            del self.buffer[:take]
        while len(out) < count:
            chunk = self.sock.recv(count - len(out))
            if not chunk:
                raise VdoApiError("VDO API closed the WebSocket connection")
            out.extend(chunk)
        return bytes(out)

    def _send_frame(self, payload: bytes, opcode: int = 0x1) -> None:
        if self.sock is None:
            raise VdoApiError("VDO API WebSocket is not connected")
        first = 0x80 | (opcode & 0x0F)
        mask_key = os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes((first, 0x80 | length))
        elif length <= 0xFFFF:
            header = bytes((first, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((first, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(header + mask_key + masked)

    def send_json(self, value: dict[str, Any]) -> None:
        self._send_frame(json.dumps(value, separators=(",", ":")).encode("utf-8"))

    def recv_json(self, timeout: float | None = None) -> dict[str, Any]:
        if self.sock is None:
            raise VdoApiError("VDO API WebSocket is not connected")
        if timeout is not None:
            self.sock.settimeout(max(0.01, timeout))
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
                payload = bytes(byte ^ mask_key[index % 4] for index, byte in enumerate(payload))
            if opcode == 0x8:
                raise VdoApiError("VDO API closed the WebSocket connection")
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
                    raise VdoApiError("VDO API sent invalid JSON") from exc
                if not isinstance(value, dict):
                    raise VdoApiError("VDO API sent a non-object JSON message")
                return value


def request(control_id: str, action: str, value: Any = _MISSING, *, timeout: float = DEFAULT_TIMEOUT, endpoint: str | None = None) -> Any:
    """Send one page-control request and wait for its correlated callback."""
    control_id = str(control_id or "").strip()
    action = str(action or "").strip()
    if not control_id:
        raise VdoApiError("missing VDO.Ninja page-control ID")
    if not action:
        raise VdoApiError("missing VDO.Ninja page-control action")

    callback_id = "os_" + uuid.uuid4().hex
    payload: dict[str, Any] = {"action": action, "cib": callback_id}
    if value is not _MISSING:
        payload["value"] = value

    deadline = time.monotonic() + timeout
    try:
        with WebSocket(endpoint or DEFAULT_ENDPOINT, timeout=timeout) as ws:
            ws.send_json({"join": control_id})
            ws.send_json(payload)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise VdoApiTimeout(f"VDO.Ninja did not answer {action}")
                try:
                    message = ws.recv_json(remaining)
                except socket.timeout as exc:
                    raise VdoApiTimeout(f"VDO.Ninja did not answer {action}") from exc
                callback = message.get("callback")
                if not isinstance(callback, dict) or callback.get("cib") != callback_id:
                    continue
                return callback.get("result")
    except VdoApiError:
        raise
    except (OSError, ssl.SSLError, socket.timeout) as exc:
        raise VdoApiError(f"VDO.Ninja control connection failed: {exc}") from exc


def probe(control_id: str, *, timeout: float = DEFAULT_TIMEOUT, endpoint: str | None = None) -> bool:
    request(control_id, "getDetails", timeout=timeout, endpoint=endpoint)
    return True


def set_mic(control_id: str, enabled: bool, *, timeout: float = DEFAULT_TIMEOUT, endpoint: str | None = None) -> bool | None:
    result = request(control_id, "mic", bool(enabled), timeout=timeout, endpoint=endpoint)
    return result if isinstance(result, bool) else None


def hangup(control_id: str, *, timeout: float = DEFAULT_TIMEOUT, endpoint: str | None = None) -> None:
    request(control_id, "hangup", True, timeout=timeout, endpoint=endpoint)
