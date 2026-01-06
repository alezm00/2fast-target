

from machine import Pin
from utime import sleep_ms
import asyncio
import random

class LedException(Exception):
    """
    Exception class for keypad-related errors.
    """
    pass


class LedManager:
    def __init__(self, row_pins, column_pins, keys):
        # if not all(isinstance(pin, Pin) for pin in row_pins):
        #     raise LedException("Row pins must be instances of Pin.")

        # if not all(isinstance(pin, Pin) for pin in column_pins):
        #     raise LedException("Column pins must be instances of Pin.")

        # if not isinstance(keys, list) or not all(isinstance(row, list) for row in keys):
        #     raise LedException("Keys must be a 2D list.")
        self.row_pins = row_pins
        self.column_pins = column_pins
        self.keys = keys


        for r in self.row_pins:
            r.init(Pin.OUT)
            r.value(0)
            print("Inizialize led row pin", r, r.value())

        for c in self.column_pins:
            c.init(Pin.OUT)
            c.value(0)
            print("Inizialize led row pin", c, c.value())


        # if len(self.row_pins) != len(self.keys) or len(self.column_pins) != len(self.keys[0]):
        #     raise LedException("Number of row/column pins does not match the key layout size.")
        # asyncio.run(self.scrollAnimation())
        # asyncio.run(self.scrollAnimation())






    async def scrollAnimation(self, delay_ms=100):
        for i in self.row_pins:
            i.value(0)
            for c in self.column_pins:
                c.value(0)
                await asyncio.sleep_ms(delay_ms)
                c.value(1)
            i.value(1)
            await asyncio.sleep_ms(delay_ms)

        await asyncio.sleep_ms(1000)
        asyncio.run(self.scrollAnimationRev(delay_ms))

    async def scrollAnimationRev(self, delay_ms=100):
        for i in self.row_pins[::-1]:
            i.value(0)
            for c in self.column_pins[::-1]:
                c.value(0)
                await asyncio.sleep_ms(delay_ms)
                c.value(1)
            i.value(1)
            await asyncio.sleep_ms(delay_ms)

    def allToggle(self, state):
        for r in self.row_pins:
            r.value(state)
        for c in self.column_pins:
            c.value(state)

    def allToggleBlink(self, times, speed):
        for i in range(times):
            self.allToggle(True)
            sleep_ms(speed)
            self.allToggle(False)
            sleep_ms(speed)

        self.allToggle(False)

    def trafficLight(self):
        for c in self.column_pins:
            c.value(0)

        for i, r in enumerate(self.row_pins):
            r.value(0)
            sleep_ms(800)
            if i == len(self.row_pins) - 1:
                sleep_ms(500 + (random.randint(0,1000)))
                r.value(0)
                break



    def clear(self):
        """Turns all LEDs off."""
        for r in self.row_pins:
            r.value(1)
        for c in self.column_pins:
            c.value(1)

    def ledON(self, index):
        for ri, row in enumerate(self.row_pins):
            for ci, col in enumerate(self.column_pins):
                if self.keys[ri][ci] == index:
                    print("ON LED pins: ", row, col, "| index:", index)
                    row.value(0)
                    col.value(0)
    def ledOFF(self, index):
        for ri, row in enumerate(self.row_pins):
            for ci, col in enumerate(self.column_pins):
                if self.keys[ri][ci] == index:
                    print("OFF LED pins: ", row, col, "| index:", index)
                    row.value(1)
                    col.value(1)

    # def clear(self):
    #     """Turns all LEDs off."""
    #     for r in self.row_pins:
    #         r.value(not self.active_high)
    #     for c in self.column_pins:
    #         c.value(self.active_high)


    # def display_led(self, index, duration_ms=10):
    #     """
    #     Turns on a specific LED (0-24).
    #     Note: In a passive matrix, you can usually only show one at a time
    #     without 'multiplexing' (scanning).
    #     """
    #     if not 0 <= index <= 24:
    #         print("Index out of range")
    #         return

    #     self.clear()

    #     row_idx = index // 5
    #     col_idx = index % 5

    #     # Turn on the specific row and column
    #     self.row_pins[row_idx].value(self.active_high)
    #     self.column_pins[col_idx].value(not self.active_high)

    #     if duration_ms > 0:
    #         sleep_ms(duration_ms)
    #         self.clear()
