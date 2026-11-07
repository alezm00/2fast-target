"""5x5 multiplexed LED matrix + on-board status LED.

A LED is lit when its row line and its column line are both active. Any set
of LEDs can be lit at once: the driver time-multiplexes by row or by column
(whichever needs fewer groups). A single group (the common case: one target
lit) is driven statically, with no flicker and full brightness.
"""
from machine import Pin


class LedMatrix:
    def __init__(self, row_pins, col_pins, active_low=True):
        self.nrows = len(row_pins)
        self.ncols = len(col_pins)
        self.active = 0 if active_low else 1
        self.idle = 1 - self.active
        self.rows = [Pin(p, Pin.OUT, value=self.idle) for p in row_pins]
        self.cols = [Pin(p, Pin.OUT, value=self.idle) for p in col_pins]
        self.mask = 0
        self._groups = []
        self._gi = 0
        self._dirty = True

    # ---- state ------------------------------------------------------------
    def set(self, mask):
        if mask != self.mask:
            self.mask = mask
            self._dirty = True

    def on(self, i):
        self.set(self.mask | (1 << i))

    def off(self, i):
        self.set(self.mask & ~(1 << i))

    def toggle(self, i):
        self.set(self.mask ^ (1 << i))

    def clear(self):
        self.set(0)

    def is_on(self, i):
        return bool(self.mask & (1 << i))

    # ---- driver -----------------------------------------------------------
    def _rebuild(self):
        rows = [0] * self.nrows   # per row: mask of columns
        cols = [0] * self.ncols   # per column: mask of rows
        for i in range(self.nrows * self.ncols):
            if self.mask & (1 << i):
                r, c = divmod(i, self.ncols)
                rows[r] |= 1 << c
                cols[c] |= 1 << r
        by_row = [(True, r, m) for r, m in enumerate(rows) if m]
        by_col = [(False, c, m) for c, m in enumerate(cols) if m]
        self._groups = by_row if len(by_row) <= len(by_col) else by_col
        self._gi = 0
        self._dirty = False
        self._static = len(self._groups) <= 1
        self._drive_needed = True

    def _drive(self, group):
        is_row, idx, sec = group
        a, d = self.active, self.idle
        if is_row:
            for r, pin in enumerate(self.rows):
                pin.value(a if r == idx else d)
            for c, pin in enumerate(self.cols):
                pin.value(a if sec & (1 << c) else d)
        else:
            for c, pin in enumerate(self.cols):
                pin.value(a if c == idx else d)
            for r, pin in enumerate(self.rows):
                pin.value(a if sec & (1 << r) else d)

    def _all_idle(self):
        d = self.idle
        for pin in self.rows:
            pin.value(d)
        for pin in self.cols:
            pin.value(d)

    def step(self):
        """Call frequently (every scan tick). Cheap when nothing changes."""
        if self._dirty:
            self._rebuild()
        if not self._groups:
            if self._drive_needed:
                self._all_idle()
                self._drive_needed = False
            return
        if self._static:
            if self._drive_needed:
                self._drive(self._groups[0])
                self._drive_needed = False
            return
        self._gi = (self._gi + 1) % len(self._groups)
        self._drive(self._groups[self._gi])


class StatusLed:
    """On-board RGB LED, optional."""
    OFF = (0, 0, 0)
    GREEN = (0, 24, 0)
    BLUE = (0, 0, 32)
    YELLOW = (32, 24, 0)
    PURPLE = (20, 0, 20)
    RED = (40, 0, 0)

    def __init__(self, pin):
        self.neo = None
        self.color = None
        if pin is None:
            return
        try:
            from machine import Pin as _Pin
            from neopixel import NeoPixel
            self.neo = NeoPixel(_Pin(pin, _Pin.OUT), 1)
            self.set(self.OFF)
        except Exception as err:  # board without neopixel: just no status LED
            print("status LED unavailable:", err)
            self.neo = None

    def set(self, color):
        if self.neo is not None and color != self.color:
            self.color = color
            self.neo[0] = color
            self.neo.write()
