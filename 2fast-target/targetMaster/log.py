from machine import Pin
from neopixel import NeoPixel
import asyncio
import utime

COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "white": (255, 255, 255),
    "purple": (128, 0, 128),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
}


class NeoLogger:
    def __init__(self, RGB_pin=48):
        self.pin = Pin(RGB_pin, Pin.OUT)
        self.neo = NeoPixel(self.pin, 1)
        self.off()

    def log(self, r, g, b):
        self.neo[0] = (r, g, b)
        self.neo.write()

    def red(self):
        self.log(*COLORS["red"])

    def green(self):
        self.log(*COLORS["green"])

    def white(self):
        self.log(*COLORS["white"])

    def purple(self):
        self.log(*COLORS["purple"])

    def blue(self):
        self.log(*COLORS["blue"])

    def yellow(self):
        self.log(*COLORS["yellow"])

    def off(self):
        self.log(0, 0, 0)

    async def blink(self, times, color="red", speed=0.5):
        rgb = COLORS.get(color, COLORS["red"])
        for _ in range(times):
            self.log(*rgb)
            await asyncio.sleep(speed)
            self.off()
            await asyncio.sleep(speed)

    def syncBlink(self, times, color="red", speed=500):
        rgb = COLORS.get(color, COLORS["red"])
        for _ in range(times):
            self.log(*rgb)
            utime.sleep_ms(speed)
            self.off()
            utime.sleep_ms(speed)
