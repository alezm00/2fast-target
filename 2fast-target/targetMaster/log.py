from machine import Pin
from neopixel import NeoPixel
import asyncio
import utime


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

    def purple(self):
        self.log(128,0,128)

    def blue(self):
        self.log(0,0,255)

    def yellow(self):
        self.log(255,255,0)

    def off(self):
        self.log(0,0,0)

    async def blink(self, times, color="red",speed=0.5):
        print("LOG: Blinking", times, "times in", color)
        for _ in range(times):
            if color=="red":
                self.red()
            elif color=="green":
                self.green()
            elif color=="white":
                self.white()
            elif color=="purple":
                self.purple()
            elif color=="blue":
                self.blue()
            elif color=="yellow":
                self.yellow()
            await asyncio.sleep(speed)
            self.off()
            await asyncio.sleep(speed)

    def syncBlink(self, times, color="red",speed=500):
        print("LOG: Blinking", times, "times in", color)
        for _ in range(times):
            if color=="red":
                self.red()
            elif color=="green":
                self.green()
            elif color=="white":
                self.white()
            utime.sleep_ms(speed)
            self.off()
            utime.sleep_ms(speed)

