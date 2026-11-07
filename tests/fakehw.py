"""Host-side stand-ins for MicroPython modules + an electrical model of the
5x5 key matrix and LED matrix, so the real firmware code can run on a PC."""
import asyncio
import os
import sys
import time
import types

ROOT = os.path.join(os.path.dirname(__file__), "..", "master")
sys.path.insert(0, os.path.abspath(ROOT))

import config  # noqa: E402  (master/config.py)

MASK = (1 << 30) - 1


class Clock:
    manual = None

    def now(self):
        if self.manual is not None:
            return self.manual & MASK
        return int(time.monotonic() * 1000) & MASK

    def set(self, ms):
        self.manual = ms

    def advance(self, ms):
        self.manual += ms

    def real(self):
        self.manual = None


CLOCK = Clock()
time.ticks_ms = CLOCK.now
time.ticks_us = lambda: CLOCK.now() * 1000
time.ticks_add = lambda a, b: (a + b) & MASK
time.ticks_diff = lambda a, b: ((a - b + (1 << 29)) & MASK) - (1 << 29)
time.sleep_ms = lambda ms: None
time.sleep_us = lambda us: None
asyncio.sleep_ms = lambda ms: asyncio.sleep(ms / 1000)


class Matrix:
    """Electrical model. `pressed` = set of physical key indices (r*5+c)."""

    def __init__(self):
        self.pressed = set()
        self.levels = {}      # pin number -> driven level (None = released/high)

    def reset(self):
        self.pressed = set()
        self.levels = {}

    def key_row_value(self, row_index):
        # union-find over rows/cols joined by closed switches
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for k in self.pressed:
            r, c = divmod(k, config.COLS)
            a, b = find(("r", r)), find(("c", c))
            parent[a] = b
        for ci, pin in enumerate(config.KEY_COL_PINS):
            if self.levels.get(pin) == 0:       # column actively pulled low
                if find(("r", row_index)) == find(("c", ci)):
                    return 0
        return 1

    def lit(self):
        """Set of LED indices currently lit by the pin levels."""
        a = 0 if config.LED_ACTIVE_LOW else 1
        out = set()
        for r, rp in enumerate(config.LED_ROW_PINS):
            for c, cp in enumerate(config.LED_COL_PINS):
                if self.levels.get(rp) == a and self.levels.get(cp) == a:
                    out.add(r * config.COLS + c)
        return out


MATRIX = Matrix()


class Pin:
    IN, OUT, OPEN_DRAIN = 0, 1, 2
    PULL_UP, PULL_DOWN = 1, 2
    IRQ_FALLING = 2

    def __init__(self, n, mode=-1, pull=-1, *, value=None):
        self.n = n
        self.mode = mode
        if value is not None:
            self.value(value)

    def init(self, mode=-1, pull=-1, *, value=None):
        self.mode = mode
        if value is not None:
            self.value(value)

    def value(self, v=None):
        if v is None:
            if self.n in config.KEY_ROW_PINS:
                return MATRIX.key_row_value(config.KEY_ROW_PINS.index(self.n))
            return MATRIX.levels.get(self.n, 1)
        if self.mode == Pin.OPEN_DRAIN:
            MATRIX.levels[self.n] = 0 if not v else None
        else:
            MATRIX.levels[self.n] = int(bool(v))

    __call__ = value


import gc  # noqa: E402
gc.mem_free = lambda: 123456


def install():
    m = types.ModuleType("machine")
    m.Pin = Pin
    m.reset = lambda: None
    m.WDT = lambda **kw: types.SimpleNamespace(feed=lambda: None)
    sys.modules["machine"] = m
    for name in ("network", "aioespnow", "neopixel"):
        sys.modules.setdefault(name, types.ModuleType(name))


install()


def press(*keys):
    MATRIX.pressed |= set(keys)


def release(*keys):
    MATRIX.pressed -= set(keys)
