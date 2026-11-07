"""Run the real master firmware on a PC with simulated hardware.

    python3 tests/sim.py [port]

Open http://localhost:8080 . Extra debug endpoint: POST /sim/press {"k": 7, "ms": 60}
(hold physical key 7 for 60 ms), used by the UI smoke test.
"""
import asyncio
import os
import sys
import tempfile

import fakehw
from fakehw import MATRIX
import config
from settings import Settings
from scoreboard import Scoreboard
from keypad import Keypad
from leds import LedMatrix
from app import App
from webserver import WebServer


class SimServer(WebServer):
    def __init__(self, *a, **kw):
        WebServer.__init__(self, *a, **kw)
        self.routes[("POST", "/sim/press")] = self.sim_press
        self.routes[("POST", "/sim/leds")] = self.sim_leds
        self.routes[("POST", "/sim/hold")] = self.sim_hold

    def sim_press(self, d):
        async def _p():
            MATRIX.pressed.add(d["k"])
            await asyncio.sleep(d.get("ms", 60) / 1000)
            MATRIX.pressed.discard(d["k"])
        asyncio.create_task(_p())
        return 200, {"ok": True}

    def sim_hold(self, d):
        MATRIX.pressed.clear()
        MATRIX.pressed.update(d.get("keys", []))
        return 200, {"ok": True}

    def sim_leds(self, d):
        return 200, {"lit": sorted(MATRIX.lit())}


async def main(port):
    tmp = tempfile.mkdtemp()
    s = Settings(os.path.join(tmp, "s.json"))
    board = Scoreboard(os.path.join(tmp, "r.json"))
    app = App(s, Keypad(config.KEY_ROW_PINS, config.KEY_COL_PINS, s),
              LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW), board)
    info = {"ap_ssid": "2FastTarget", "ap_ip": "192.168.4.1", "sta_ip": "", "sta_ssid": "", "channel": 1,
            "ap_mac": "aa:bb:cc:dd:ee:01", "sta_mac": "aa:bb:cc:dd:ee:00"}
    web = SimServer(app, info, port, os.path.join(os.path.dirname(__file__), "..", "master", "web"))
    await asyncio.gather(app.run(), web.serve())


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    try:
        asyncio.run(main(port))
    except KeyboardInterrupt:
        pass
