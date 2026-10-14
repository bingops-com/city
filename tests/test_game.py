import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace

from citygame.__main__ import Handler
from citygame.game import Game
from citysim.engine import RuleError


class Socket:
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.file = Path(self.temp.name) / "city.sqlite"
        self.game = Game(self.file)

    def tearDown(self):
        self.game.close()
        self.temp.cleanup()

    def install(self):
        self.game.command("home_0001", "home", {"home": "home_garden"})
        self.game.command("job_00001", "job", {"job": "gardener"})

    def request(self, path, method="GET", body=None, auth=False, origin="http://localhost:8092"):
        data = json.dumps(body).encode() if body is not None else b""
        headers = f"Host: localhost:8092\r\nOrigin: {origin}\r\nContent-Length: {len(data)}\r\nContent-Type: application/json\r\n"
        if auth:
            headers += f"Cookie: city_session={self.game.token}\r\n"
        socket = Socket(f"{method} {path} HTTP/1.0\r\n{headers}\r\n".encode() + data)
        with redirect_stderr(io.StringIO()):
            Handler(socket, ("127.0.0.1", 1), SimpleNamespace(game=self.game, server_port=8092))
        head, response = bytes(socket.output).split(b"\r\n\r\n", 1)
        return int(head.split()[1]), json.loads(response) if path.startswith("/api/") else response

    def test_two_choices_enable_automatic_routine(self):
        self.install()
        before = self.game.sim.ledger.balances[self.game.player_id]
        self.game.command("advance_001", "advance", {})
        snapshot = self.game.snapshot()
        self.assertTrue(snapshot["player"]["routine_enabled"])
        self.assertEqual(snapshot["world"]["day"], 1)
        self.assertGreater(snapshot["player"]["cash_cents"], before)
        self.assertEqual(self.game.player.missed_food, 0)

    def test_repeated_command_does_not_advance_twice(self):
        self.install()
        first = self.game.command("advance_001", "advance", {})
        second = self.game.command("advance_001", "advance", {})
        self.assertEqual(first, second)
        self.assertEqual(self.game.sim.day, 1)
        with self.assertRaises(RuleError):
            self.game.command("advance_001", "advance", {"changed": True})

    def test_restart_replays_accounting_and_goal_exactly(self):
        self.install()
        self.game.command("advance_001", "advance", {})
        self.game.command("goal_00001", "goal", {"goal": "garden"})
        self.game.move(11, 27)
        self.game.command("build_0001", "complete_goal", {})
        expected = self.game.snapshot()
        self.game.close()
        self.game = Game(self.file)
        self.assertEqual(self.game.snapshot(), expected)
        self.game.sim.ledger.check()
        self.game.sim.stocks.check()

    def test_optional_goal_spends_real_money_and_cannot_repeat(self):
        self.install()
        self.game.command("goal_00001", "goal", {"goal": "bench"})
        self.game.move(33, 27)
        before = self.game.sim.ledger.balances[self.game.player_id]
        self.game.command("build_0001", "complete_goal", {})
        self.assertEqual(before - self.game.sim.ledger.balances[self.game.player_id], 800)
        digest = self.game.digest()
        with self.assertRaises(RuleError):
            self.game.command("build_0002", "complete_goal", {})
        self.assertEqual(self.game.digest(), digest)

    def test_failed_goal_leaves_account_and_save_unchanged(self):
        self.install()
        self.game.command("goal_00001", "goal", {"goal": "bench"})
        digest = self.game.digest()
        with self.assertRaises(RuleError):
            self.game.command("build_0001", "complete_goal", {})
        self.assertEqual(self.game.digest(), digest)
        self.assertNotIn("session", self.game.backup())

    def test_private_budget_requires_session_and_public_map_does_not_expose_accounts(self):
        status, renderer = self.request("/scene.js")
        self.assertEqual(status, 200)
        self.assertIn(b"class CityScene", renderer)
        status, private = self.request("/api/me")
        self.assertEqual(status, 401)
        status, public = self.request("/api/world")
        self.assertEqual(status, 200)
        self.assertNotIn("player", public)
        self.assertNotIn("accounts", public)
        self.assertNotIn("cash_cents", public)
        status, private = self.request("/api/me", auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(private["player"]["cash_cents"], 30000)

    def test_foreign_origin_cannot_change_game(self):
        before = self.game.digest()
        status, _ = self.request("/api/action", "POST", {"id": "home_0001", "action": "home", "payload": {"home": "home_garden"}}, auth=True, origin="https://elsewhere.test")
        self.assertEqual(status, 403)
        self.assertEqual(self.game.digest(), before)

    def test_collision_and_invalid_positions_are_rejected(self):
        for x, y in ((20, 6), (41, 22), (True, 19), (-1, 19), (22.1, 19)):
            with self.subTest(x=x, y=y):
                with self.assertRaises(RuleError):
                    self.game.move(x, y)

    def test_offline_restart_does_not_create_expenses_or_advance_time(self):
        self.install()
        expected = self.game.snapshot()
        self.game.close()
        self.game = Game(self.file)
        self.assertEqual(self.game.snapshot(), expected)

    def test_export_can_restore_into_new_database(self):
        self.install()
        self.game.command("advance_001", "advance", {})
        self.game.command("goal_00001", "goal", {"goal": "bench"})
        self.game.move(33, 27)
        self.game.command("build_0001", "complete_goal", {})
        backup = self.game.backup()
        restored = Game(Path(self.temp.name) / "restored.sqlite")
        try:
            restored.restore_backup(backup)
            self.assertEqual(restored.snapshot(), self.game.snapshot())
        finally:
            restored.close()

    def test_tampered_restore_rolls_back_the_whole_import(self):
        self.install()
        backup = self.game.backup()
        backup["commands"][-1]["digest"] = "modified"
        restored = Game(Path(self.temp.name) / "restored.sqlite")
        try:
            with self.assertRaises(RuleError):
                restored.restore_backup(backup)
            self.assertEqual(restored.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0], 0)
            self.assertIsNone(restored.home)
        finally:
            restored.close()


if __name__ == "__main__":
    unittest.main()
