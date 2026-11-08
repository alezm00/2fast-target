"""Physical START button (GPIO in config.BTN_START_PIN) with software debounce.

Starts the game currently selected in the web interface. It never stops a game
(stopping is done from the web page), so an accidental press while playing is harmless."""
import asyncio
from machine import Pin

POLL_MS = 10
STABLE_N = 4   # 40 ms of stable level


class StartButton:
    def __init__(self, app, pin):
        self.app = app
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP) if pin is not None else None
        self.level = 1
        self.count = 0

    async def run(self):
        if self.pin is None:
            return
        while True:
            level = self.pin.value()
            if level == self.level:
                self.count = 0
            else:
                self.count += 1
                if self.count >= STABLE_N:
                    self.level = level
                    self.count = 0
                    if level == 0:       # pressed
                        ok, msg = self.app.cmd_start(None, "button")
                        print("START button:", "ok" if ok else msg)
            await asyncio.sleep_ms(POLL_MS)
