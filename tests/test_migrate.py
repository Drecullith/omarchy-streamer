#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("migrate", ROOT / "bin" / "migrate.py")
assert SPEC and SPEC.loader
migrate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migrate)


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        base = Path(self.tempdir.name)
        migrate.STATE_ROOT = base / "state" / "omarchy-streamer"
        migrate.CONFIG_ROOT = base / "config" / "omarchy-streamer"
        migrate.MARKER = migrate.STATE_ROOT / "state-schema.json"

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_repairs_permissions_and_preserves_unknown_files(self) -> None:
        migrate.STATE_ROOT.mkdir(parents=True)
        migrate.CONFIG_ROOT.mkdir(parents=True)
        secret = migrate.STATE_ROOT / "collab-session.json"
        secret.write_text('{"password":"keep-me"}\n', encoding="utf-8")
        secret.chmod(0o644)
        unknown = migrate.STATE_ROOT / "user-note.txt"
        unknown.write_text("do not delete\n", encoding="utf-8")
        result = migrate.migrate()
        self.assertTrue(result["ok"])
        self.assertTrue(unknown.exists())
        self.assertEqual(stat.S_IMODE(secret.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(migrate.STATE_ROOT.stat().st_mode), 0o700)
        marker = json.loads(migrate.MARKER.read_text(encoding="utf-8"))
        self.assertEqual(marker["schemaVersion"], 1)
        self.assertEqual(stat.S_IMODE(migrate.MARKER.stat().st_mode), 0o600)

    def test_newer_schema_fails_closed(self) -> None:
        migrate.STATE_ROOT.mkdir(parents=True)
        migrate.MARKER.write_text('{"schemaVersion":99}\n', encoding="utf-8")
        result = migrate.migrate()
        self.assertFalse(result["ok"])
        self.assertEqual(result["schemaVersion"], 99)


if __name__ == "__main__":
    unittest.main()
