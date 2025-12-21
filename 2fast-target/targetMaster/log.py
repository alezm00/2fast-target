from machine import Pin
from neopixel import NeoPixel
import asyncio



class NeoLogger:
    def __init__(self,RGB_pin=48):
        self.pin = Pin(RGB_pin, Pin.OUT)
        self.neo = NeoPixel(self.pin, 1)
        self.neo[0] = (0, 0, 0)
        self.neo.write()

    def log(self, r, g, b):
        self.neo[0] = (r, g, b)
        self.neo.write()

    def red(self):
        self.log(255,0,0)

    def green(self):
        self.log(0,255,0)

    def white(self):
        self.log(255,255,255)

    def off(self):
        self.log(0,0,0)

    async def _blink(self, times, color):
        print("Blinking", times, "times in", color)
        for _ in range(times):
            if color=="red":
                self.red()
            elif color=="green":
                self.green()
            elif color=="white":
                self.white()
            await asyncio.sleep(0.2)
            self.off()
            await asyncio.sleep(0.5)

    def blink(self, times, color="red"):
        asyncio.run(self._blink(times, color))
