"""Local physical buttons (start/stop) with software debounce."""
import asyncio
from machine import Pin

POLL_MS = 10
STABLE_N = 4   # 40 ms


class Buttons:
    def __init__(self, app, start_pin, stop_pin):
        self.app = app
        self.items = []
        for pin, action in ((start_pin, "toggle"), (stop_pin, "stop")):
            if pin is not None:
                self.items.append([Pin(pin, Pin.IN, Pin.PULL_UP), action, 1, 0])

    async def run(self):
        if not self.items:
            return
        while True:
            for it in self.items:
                level = it[0].value()
                if level == it[2]:
                    it[3] = 0
                else:
                    it[3] += 1
                    if it[3] >= STABLE_N:
                        it[2] = level
                        it[3] = 0
                        if level == 0:   # pressed
                            if it[1] == "stop":
                                self.app.cmd_stop("button")
                            else:
                                self.app.cmd_toggle("button")
            await asyncio.sleep_ms(POLL_MS)
