"""End-to-end: real firmware modules + real HTTP server on localhost,
hardware replaced by the electrical model."""
import asyncio
import json
import os
import tempfile
import unittest

import fakehw
from fakehw import CLOCK, MATRIX
import config
from settings import Settings
from scoreboard import Scoreboard
from keypad import Keypad
from leds import LedMatrix
from app import App
from webserver import WebServer
from buttons import StartButton

PORT = 18080


async def http(method, path, body=None):
    r, w = await asyncio.open_connection("127.0.0.1", PORT)
    data = json.dumps(body).encode() if body is not None else b""
    w.write(("%s %s HTTP/1.1\r\nHost: x\r\nContent-Length: %d\r\n\r\n" % (method, path, len(data))).encode() + data)
    await w.drain()
    raw = await r.read()
    w.close()
    head, _, payload = raw.partition(b"\r\n\r\n")
    code = int(head.split()[1])
    try:
        return code, json.loads(payload)
    except ValueError:
        return code, payload


class SystemTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        CLOCK.real()
        MATRIX.reset()
        self.tmp = tempfile.mkdtemp()
        self.settings = Settings(os.path.join(self.tmp, "s.json"))
        self.settings.update({"countdown_enabled": False, "finish_blink": False}, persist=False)
        self.board = Scoreboard(os.path.join(self.tmp, "r.json"))
        leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
        kp = Keypad(config.KEY_ROW_PINS, config.KEY_COL_PINS, self.settings)
        self.app = App(self.settings, kp, leds, self.board)
        self.rebooted = []
        info = {"ap_ssid": "x", "ap_ip": "192.168.4.1", "channel": 1}
        self.web = WebServer(self.app, info, PORT, os.path.join(os.path.dirname(__file__), "..", "master", "web"),
                             lambda: self.rebooted.append(1))
        self.tasks = [asyncio.create_task(self.app.run()), asyncio.create_task(self.web.serve())]
        await asyncio.sleep(0.15)

    async def asyncTearDown(self):
        for t in self.tasks:
            t.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        if self.web.server:
            self.web.server.close()

    async def tap(self, key, ms=45):
        MATRIX.pressed.add(key)
        await asyncio.sleep(ms / 1000)
        MATRIX.pressed.discard(key)
        await asyncio.sleep(0.03)

    def lit_now(self):
        lit = MATRIX.lit()
        return lit

    async def test_static_page_and_routes(self):
        code, page = await http("GET", "/")
        self.assertEqual(code, 200)
        self.assertIn(b"2Fast", page)
        self.assertEqual((await http("GET", "/nope"))[0], 404)
        self.assertEqual((await http("DELETE", "/api/state"))[0], 405)
        code, info = await http("GET", "/api/info")
        self.assertEqual(code, 200)
        self.assertEqual([m["id"] for m in info["modes"]], ["sequence", "reflex", "timed", "multi", "demo"])

    async def test_bad_requests_do_not_hurt(self):
        r, w = await asyncio.open_connection("127.0.0.1", PORT)
        w.write(b"garbage\r\n\r\n")
        await w.drain()
        self.assertIn(b"400", await r.read())
        w.close()
        code, _ = await http("POST", "/api/config", ["not", "an", "object"])
        self.assertEqual(code, 400)
        r, w = await asyncio.open_connection("127.0.0.1", PORT)
        w.write(b"POST /api/start HTTP/1.1\r\nContent-Length: 99999\r\n\r\n")
        await w.drain()
        self.assertIn(b"413", await r.read())
        w.close()
        self.assertEqual((await http("GET", "/api/state"))[0], 200)

    async def play_to_the_end(self):
        for _ in range(60):
            st = (await http("GET", "/api/state"))[1]
            if st["phase"] != "running":
                return st
            lit = self.lit_now()
            if len(lit) == 1:
                await self.tap(next(iter(lit)))
            else:
                await asyncio.sleep(0.01)
        self.fail("game did not finish")

    async def test_full_sequence_game_via_web(self):
        code, _ = await http("POST", "/api/start", {"mode": "sequence"})
        self.assertEqual(code, 200)
        self.assertEqual((await http("POST", "/api/start", {"mode": "sequence"}))[0], 409)   # already running
        st = await self.play_to_the_end()
        self.assertEqual((st["phase"], st["hits"], st["miss"]), ("finished", 25, 0))
        self.assertGreater(st["el"], 0)
        _, res = await http("GET", "/api/result")
        r = res["result"]
        self.assertEqual(len(r["rt"]), 25)
        self.assertEqual(sum(r["rt"]), r["total"])
        self.assertEqual(MATRIX.lit(), set())
        _, rs = await http("GET", "/api/results")
        self.assertEqual(rs["best"]["sequence"]["v"], r["total"])

    async def test_wrong_target_counts_error_not_hit(self):
        await http("POST", "/api/start", {"mode": "sequence"})
        await asyncio.sleep(0.05)
        lit = next(iter(self.lit_now()))
        await self.tap((lit + 1) % 25)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual((st["hits"], st["err"]), (0, 1))

    async def test_selected_game_is_started_by_web_and_by_the_start_button(self):
        # the game is configured from the web interface and stored on the device
        code, _ = await http("POST", "/api/config", {"default_mode": "timed", "timed_duration_s": 9})
        self.assertEqual(code, 200)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual(st["armed"], "timed")

        button = StartButton(self.app, config.BTN_START_PIN)
        self.tasks.append(asyncio.create_task(button.run()))

        async def press_button(ms=120):
            MATRIX.levels[config.BTN_START_PIN] = 0
            await asyncio.sleep(ms / 1000)
            MATRIX.levels[config.BTN_START_PIN] = 1
            await asyncio.sleep(0.08)

        MATRIX.levels[config.BTN_START_PIN] = 1
        await asyncio.sleep(0.05)
        await press_button()
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual((st["phase"], st["mode"], st["cmd"][0]), ("running", "timed", "button"))
        self.assertEqual(self.app.session.game.duration, 9000)

        # pressing START during a game does not stop it, nor restart it
        t0 = self.app.session.game.t0
        await press_button()
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual(st["phase"], "running")
        self.assertEqual(self.app.session.game.t0, t0)

        # stopping is done from the web page; then the same game starts again from the button or the site
        self.assertEqual((await http("POST", "/api/stop"))[0], 200)
        self.assertEqual((await http("GET", "/api/state"))[1]["phase"], "finished")
        await http("POST", "/api/config", {"default_mode": "demo"})
        await press_button()
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual((st["phase"], st["mode"]), ("running", "demo"))
        await http("POST", "/api/stop")
        code, _ = await http("POST", "/api/start", {})          # web start = selected game too
        self.assertEqual(code, 200)
        self.assertEqual((await http("GET", "/api/state"))[1]["mode"], "demo")
        self.assertEqual((await http("POST", "/api/start", {"mode": "zzz"}))[0], 400)

    async def test_start_button_ignored_in_test_mode(self):
        await http("POST", "/api/appmode", {"mode": "test"})
        button = StartButton(self.app, config.BTN_START_PIN)
        self.tasks.append(asyncio.create_task(button.run()))
        MATRIX.levels[config.BTN_START_PIN] = 1
        await asyncio.sleep(0.05)
        MATRIX.levels[config.BTN_START_PIN] = 0
        await asyncio.sleep(0.12)
        MATRIX.levels[config.BTN_START_PIN] = 1
        await asyncio.sleep(0.05)
        self.assertEqual((await http("GET", "/api/state"))[1]["phase"], "idle")

    async def test_config_api(self):
        code, r = await http("POST", "/api/config", {"seq_timeout_ms": 4000})
        self.assertEqual((code, r["changed"], r["reboot"]), (200, ["seq_timeout_ms"], False))
        code, r = await http("POST", "/api/config", {"ap_channel": 6})
        self.assertTrue(r["reboot"])
        code, r = await http("POST", "/api/config", {"seq_timeout_ms": 1})
        self.assertEqual(code, 400)
        self.assertIn("seq_timeout_ms", r["errors"])
        self.assertEqual((await http("GET", "/api/config"))[1]["values"]["seq_timeout_ms"], 4000)
        code, _ = await http("POST", "/api/config/reset")
        self.assertEqual(self.settings["seq_timeout_ms"], 5000)

    async def test_test_mode_shows_matrix_and_controls_leds(self):
        self.assertEqual((await http("POST", "/api/test/led", {"i": 3, "on": True}))[0], 409)   # not in test mode
        self.assertEqual((await http("POST", "/api/appmode", {"mode": "test"}))[0], 200)
        self.assertEqual((await http("POST", "/api/start", {"mode": "sequence"}))[0], 409)      # no games in test
        await http("POST", "/api/test/led", {"i": 3, "on": True})
        await http("POST", "/api/test/led", {"i": 20, "on": True})
        await asyncio.sleep(0.05)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual(st["lit"], (1 << 3) | (1 << 20))
        seen = set()
        for _ in range(30):
            self.app.leds.step()
            seen |= MATRIX.lit()
        self.assertEqual(seen, {3, 20})
        MATRIX.pressed.add(8)
        await asyncio.sleep(0.05)
        st = (await http("GET", "/api/state"))[1]
        self.assertTrue(st["down"] >> 8 & 1)
        MATRIX.pressed.discard(8)
        await asyncio.sleep(0.05)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual((st["down"], st["presses"][8]), (0, 1))
        await http("POST", "/api/test/led", {"pattern": "all"})
        await asyncio.sleep(0.05)
        self.assertEqual((await http("GET", "/api/state"))[1]["lit"], (1 << 25) - 1)
        await http("POST", "/api/test/led", {"pattern": "chase"})
        await asyncio.sleep(0.1)
        self.assertEqual(bin((await http("GET", "/api/state"))[1]["lit"]).count("1"), 1)
        await http("POST", "/api/appmode", {"mode": "play"})
        await asyncio.sleep(0.05)
        self.assertEqual(MATRIX.lit(), set())

    async def test_calibration_wizard_learns_permuted_wiring(self):
        # wiring is reversed: pressing key (24 - t) answers LED t; key 7 is missing/dead (skip LED 17)
        await http("POST", "/api/appmode", {"mode": "test"})
        self.assertEqual((await http("POST", "/api/test/learn", {"action": "start"}))[0], 200)
        for t in range(25):
            await asyncio.sleep(0.04)
            st = (await http("GET", "/api/state"))[1]
            self.assertEqual(st["app"], "learn")
            self.assertEqual(MATRIX.lit(), {t})
            if t == 17:
                await http("POST", "/api/test/learn", {"action": "skip"})
            else:
                await self.tap(24 - t)
        await asyncio.sleep(0.05)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual(st["app"], "test")
        km = self.settings.keymap
        self.assertEqual(sorted(km), list(range(25)))               # still a permutation
        self.assertEqual([km[t] for t in range(25) if t != 17], [24 - t for t in range(25) if t != 17])
        self.assertFalse(self.settings.enabled[17])
        self.assertEqual(sum(self.settings.enabled), 24)
        # the learned map is persisted
        s2 = Settings(self.settings.path)
        s2.load()
        self.assertEqual(s2.keymap, km)
        # and used in play: LED t must be answered by key 24 - t
        await http("POST", "/api/appmode", {"mode": "play"})
        await http("POST", "/api/start", {"mode": "sequence"})
        await asyncio.sleep(0.05)
        t = next(iter(MATRIX.lit()))
        await self.tap(24 - t)
        self.assertEqual((await http("GET", "/api/state"))[1]["hits"], 1)

    async def test_learn_rejects_duplicate_key_and_can_cancel(self):
        await http("POST", "/api/appmode", {"mode": "test"})
        await http("POST", "/api/test/learn", {"action": "start"})
        await asyncio.sleep(0.03)
        await self.tap(5)
        await asyncio.sleep(0.03)
        await self.tap(5)
        st = (await http("GET", "/api/state"))[1]
        self.assertEqual(st["learn"]["i"], 1)
        self.assertIn("già assegnato", st["learn"]["msg"])
        await http("POST", "/api/test/learn", {"action": "cancel"})
        self.assertEqual((await http("GET", "/api/state"))[1]["app"], "test")
        self.assertEqual(self.settings.keymap, list(range(25)))     # untouched

    async def test_timing_is_precise_with_http_load(self):
        """Reaction times must not be distorted by web traffic."""
        self.settings.update({"seq_timeout_ms": 5000}, persist=False)
        await http("POST", "/api/start", {"mode": "sequence"})
        await asyncio.sleep(0.05)
        async def hammer():
            for _ in range(30):
                await http("GET", "/api/state")
        h = asyncio.create_task(hammer())
        lit = next(iter(self.lit_now()))
        t0 = CLOCK.now()
        await asyncio.sleep(0.3)
        MATRIX.pressed.add(lit)
        await asyncio.sleep(0.1)
        MATRIX.pressed.discard(lit)
        await h
        rt = self.app.session.game.rt[0]
        # reaction measured ≈ time from lighting to first contact (~0.35 s since start of game), not detection
        self.assertTrue(300 <= rt <= 450, rt)


if __name__ == "__main__":
    unittest.main()
