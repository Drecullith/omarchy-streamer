#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import socket
import struct
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vdoapi", ROOT / "bin" / "vdoapi.py")
assert SPEC and SPEC.loader
vdoapi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vdoapi)


def server_frame(value: dict) -> bytes:
    payload = json.dumps(value, separators=(",", ":")).encode()
    length = len(payload)
    if length < 126:
        return bytes((0x81, length)) + payload
    return bytes((0x81, 126)) + struct.pack("!H", length) + payload


def read_exact(conn: socket.socket, count: int) -> bytes:
    out = bytearray()
    while len(out) < count:
        chunk = conn.recv(count - len(out))
        if not chunk:
            raise EOFError
        out.extend(chunk)
    return bytes(out)


def client_frame(conn: socket.socket) -> tuple[int, dict | None]:
    head = read_exact(conn, 2)
    opcode = head[0] & 0x0F
    length = head[1] & 0x7F
    masked = bool(head[1] & 0x80)
    if length == 126:
        length = struct.unpack("!H", read_exact(conn, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_exact(conn, 8))[0]
    mask = read_exact(conn, 4) if masked else b""
    payload = read_exact(conn, length)
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    if opcode != 1:
        return opcode, None
    return opcode, json.loads(payload.decode())


class FakeVdoApi:
    def __init__(self, answer: bool = True) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.2)
        self.port = self.listener.getsockname()[1]
        self.answer = answer
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.seen_join = ""
        self.actions: list[dict] = []

    @property
    def endpoint(self) -> str:
        return f"ws://127.0.0.1:{self.port}/"

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.listener.close()
        self.thread.join(timeout=2)

    def run(self) -> None:
        while not self.stop_event.is_set():
            try:
                conn, _ = self.listener.accept()
            except (socket.timeout, OSError):
                continue
            try:
                self.handle(conn)
            except (EOFError, OSError, json.JSONDecodeError):
                pass
            finally:
                conn.close()

    def handle(self, conn: socket.socket) -> None:
        conn.settimeout(1)
        raw = bytearray()
        while b"\r\n\r\n" not in raw:
            raw.extend(conn.recv(4096))
        headers = raw.decode("latin1")
        key = ""
        for line in headers.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
                break
        accept = base64.b64encode(hashlib.sha1((key + vdoapi.GUID).encode()).digest()).decode()
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode()
        conn.sendall(response)

        _, join = client_frame(conn)
        assert join and "join" in join
        self.seen_join = str(join["join"])
        _, action = client_frame(conn)
        assert action and action.get("action")
        self.actions.append(action)
        if not self.answer:
            time.sleep(0.3)
            return
        name = str(action["action"])
        if name == "getDetails":
            result = {"page": "online"}
        elif name == "mic":
            result = bool(action.get("value"))
        elif name == "hangup":
            result = True
        else:
            result = None
        conn.sendall(server_frame({"callback": {"cib": action.get("cib"), "action": name, "result": result}}))


class VdoApiTests(unittest.TestCase):
    def test_probe_requires_callback_from_target_page(self) -> None:
        server = FakeVdoApi()
        server.start()
        try:
            self.assertTrue(vdoapi.probe("private-control", endpoint=server.endpoint, timeout=0.5))
            self.assertEqual(server.seen_join, "private-control")
            self.assertEqual(server.actions[0]["action"], "getDetails")
        finally:
            server.stop()

    def test_mic_state_comes_from_correlated_callback(self) -> None:
        server = FakeVdoApi()
        server.start()
        try:
            self.assertFalse(vdoapi.set_mic("private-control", False, endpoint=server.endpoint, timeout=0.5))
            self.assertTrue(vdoapi.set_mic("private-control", True, endpoint=server.endpoint, timeout=0.5))
        finally:
            server.stop()

    def test_hangup_uses_private_page_control_channel(self) -> None:
        server = FakeVdoApi()
        server.start()
        try:
            vdoapi.hangup("private-control", endpoint=server.endpoint, timeout=0.5)
            self.assertEqual(server.actions[-1]["action"], "hangup")
            self.assertIs(server.actions[-1]["value"], True)
        finally:
            server.stop()

    def test_timeout_is_not_reported_as_online(self) -> None:
        server = FakeVdoApi(answer=False)
        server.start()
        try:
            with self.assertRaises(vdoapi.VdoApiTimeout):
                vdoapi.probe("private-control", endpoint=server.endpoint, timeout=0.08)
        finally:
            server.stop()

    def test_invalid_endpoint_is_rejected(self) -> None:
        with self.assertRaises(vdoapi.VdoApiError):
            vdoapi.WebSocket("https://api.vdo.ninja/")


if __name__ == "__main__":
    unittest.main()
