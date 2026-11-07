from machine import Pin
from utime import sleep_ms
import asyncio
import random


class LedException(Exception):
    """Exception class for LED-related errors."""
    pass


class LedManager:
    """Drives a 5x5 LED matrix (rows active LOW, columns active LOW)."""

    def __init__(self, row_pins, column_pins, keys):
        if not keys or len(row_pins) != len(keys) or any(len(r) != len(column_pins) for r in keys):
            raise LedException("Number of row/column pins does not match the key layout size.")

        self.row_pins = row_pins
        self.column_pins = column_pins
        self.keys = keys

        # key label -> (row, col), so ledON/ledOFF don't scan the whole matrix
        self._pos = {}
        for ri, row in enumerate(keys):
            for ci, label in enumerate(row):
                self._pos[label] = (ri, ci)

        for pin in self.row_pins + self.column_pins:
            pin.init(Pin.OUT)
        self.clear()

    async def scrollAnimation(self, delay_ms=100):
        for r in self.row_pins:
            r.value(0)
            for c in self.column_pins:
                c.value(0)
                await asyncio.sleep_ms(delay_ms)
                c.value(1)
            r.value(1)
            await asyncio.sleep_ms(delay_ms)

        await asyncio.sleep_ms(1000)
        await self.scrollAnimationRev(delay_ms)

    async def scrollAnimationRev(self, delay_ms=100):
        for r in self.row_pins[::-1]:
            r.value(0)
            for c in self.column_pins[::-1]:
                c.value(0)
                await asyncio.sleep_ms(delay_ms)
                c.value(1)
            r.value(1)
            await asyncio.sleep_ms(delay_ms)

    def allToggle(self, state):
        # active LOW: state True -> everything lit
        v = 0 if state else 1
        for pin in self.row_pins + self.column_pins:
            pin.value(v)

    def allToggleBlink(self, times, speed):
        for _ in range(times):
            self.allToggle(True)
            sleep_ms(speed)
            self.allToggle(False)
            sleep_ms(speed)
        self.allToggle(False)

    async def trafficLight(self):
        """Light the rows one by one, then wait a random time (race start)."""
        for c in self.column_pins:
            c.value(0)

        for r in self.row_pins:
            r.value(0)
            await asyncio.sleep_ms(800)

        await asyncio.sleep_ms(500 + random.randint(0, 1000))

    def clear(self):
        """Turns all LEDs off."""
        for pin in self.row_pins + self.column_pins:
            pin.value(1)

    def ledON(self, index):
        pos = self._pos.get(index)
        if pos is None:
            return
        self.row_pins[pos[0]].value(0)
        self.column_pins[pos[1]].value(0)

    def ledOFF(self, index):
        pos = self._pos.get(index)
        if pos is None:
            return
        self.row_pins[pos[0]].value(1)
        self.column_pins[pos[1]].value(1)
