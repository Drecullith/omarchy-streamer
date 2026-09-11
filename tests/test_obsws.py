#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import socket
import struct
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("obsws", ROOT / "bin" / "obsws.py")
assert spec and spec.loader
obsws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(obsws)


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
        payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
    if opcode != 1:
        return opcode, None
    return opcode, json.loads(payload.decode())


class FakeObs:
    def __init__(self) -> None:
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.2)
        self.port = self.listener.getsockname()[1]
        self.streaming = False
        self.recording = False
        self.replay = False
        self.scene = "Gameplay"
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

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
        accept = base64.b64encode(hashlib.sha1((key + obsws.GUID).encode()).digest()).decode()
        upgrade = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode()
        hello = server_frame({"op": 0, "d": {"obsWebSocketVersion": "5.test", "rpcVersion": 1}})
        # Deliberately coalesce the upgrade and Hello to catch lost-buffer bugs.
        conn.sendall(upgrade + hello)

        opcode, identify = client_frame(conn)
        assert opcode == 1 and identify and identify.get("op") == 1
        conn.sendall(server_frame({"op": 2, "d": {"negotiatedRpcVersion": 1}}))

        while True:
            opcode, message = client_frame(conn)
            if opcode == 8:
                return
            if opcode != 1 or not message or message.get("op") != 6:
                continue
            req = message["d"]
            request_type = req["requestType"]
            request_data = req.get("requestData") or {}
            response_data: dict = {}
            ok = True
            comment = ""

            if request_type == "GetStreamStatus":
                response_data = {"outputActive": self.streaming}
            elif request_type == "StartStream":
                self.streaming = True
            elif request_type == "StopStream":
                self.streaming = False
            elif request_type == "GetRecordStatus":
                response_data = {"outputActive": self.recording}
            elif request_type == "StartRecord":
                self.recording = True
            elif request_type == "StopRecord":
                self.recording = False
            elif request_type == "GetReplayBufferStatus":
                response_data = {"outputActive": self.replay}
            elif request_type == "StartReplayBuffer":
                self.replay = True
            elif request_type == "StopReplayBuffer":
                self.replay = False
            elif request_type == "SaveReplayBuffer":
                ok = self.replay
                comment = "Replay buffer is not active" if not ok else ""
            elif request_type == "GetSceneList":
                response_data = {"currentProgramSceneName": self.scene, "scenes": [{"sceneName": self.scene}]}
            elif request_type == "SetCurrentProgramScene":
                self.scene = str(request_data.get("sceneName", ""))
                ok = bool(self.scene)
            else:
                ok = False
                comment = "unknown request"

            status = {"result": ok, "code": 100 if ok else 600}
            if comment:
                status["comment"] = comment
            response = {
                "op": 7,
                "d": {
                    "requestType": request_type,
                    "requestId": req["requestId"],
                    "requestStatus": status,
                    "responseData": response_data,
                },
            }
            conn.sendall(server_frame(response))


class ObsWsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = FakeObs()
        self.server.start()
        self.env = patch.dict(
            os.environ,
            {
                "OMARCHY_STREAMER_OBS_HOST": "127.0.0.1",
                "OMARCHY_STREAMER_OBS_PORT": str(self.server.port),
                "OMARCHY_STREAMER_OBS_PASSWORD": "",
                "OMARCHY_STREAMER_OBS_CONFIG": "/definitely/not/present/config.json",
            },
            clear=False,
        )
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.server.stop()

    def test_status_and_actions(self) -> None:
        state = obsws.status()
        self.assertTrue(state["connected"])
        self.assertFalse(state["streaming"])
        self.assertEqual(state["currentScene"], "Gameplay")

        obsws.perform("stream.start")
        self.assertTrue(obsws.status()["streaming"])
        obsws.perform("record.start")
        self.assertTrue(obsws.status()["recording"])
        obsws.perform("replay.start")
        self.assertTrue(obsws.status()["replayBuffer"])
        obsws.perform("clip.save")
        obsws.perform("scene.set", "BRB")
        self.assertEqual(obsws.status()["currentScene"], "BRB")

    def test_remote_host_requires_explicit_opt_in(self) -> None:
        with patch.dict(os.environ, {"OMARCHY_STREAMER_OBS_HOST": "192.0.2.1"}, clear=False):
            os.environ.pop("OMARCHY_STREAMER_OBS_ALLOW_REMOTE", None)
            with self.assertRaises(obsws.ObsError):
                obsws.load_connection()


if __name__ == "__main__":
    unittest.main()
