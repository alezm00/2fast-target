"""Fault-tolerant scanner for the target switch matrix.

Protections against bad readings:
  * integrating debounce (a one-scan glitch never registers as a hit)
  * timestamp of the *first* contact is kept, so debounce latency does not
    distort reaction times
  * ghost / ambiguous keys filtered (3 keys pressed on a rectangle corner)
  * stuck keys (held longer than `stuck_ms`, shorted line...) are masked
    until released, so they cannot trigger hits
  * if far too many keys read pressed at once the scan is treated as noise
"""
from machine import Pin
from time import sleep_us, ticks_diff

NOISE_LIMIT = 12   # more simultaneous keys than this = electrical fault


def popcount(x):
    n = 0
    while x:
        x &= x - 1
        n += 1
    return n


class Keypad:
    def __init__(self, row_pins, col_pins, settings):
        self.nrows = len(row_pins)
        self.ncols = len(col_pins)
        self.n = self.nrows * self.ncols
        self.rows = [Pin(p, Pin.IN, Pin.PULL_UP) for p in row_pins]
        # open drain: a line is either pulled low or released, so two
        # simultaneously pressed keys can never short two driven outputs
        self.cols = [Pin(p, Pin.OPEN_DRAIN, value=1) for p in col_pins]
        self.s = settings

        self.row_masks = []
        self.col_masks = []
        for r in range(self.nrows):
            self.row_masks.append(sum(1 << (r * self.ncols + c) for c in range(self.ncols)))
        for c in range(self.ncols):
            self.col_masks.append(sum(1 << (r * self.ncols + c) for r in range(self.nrows)))

        self.cnt = [0] * self.n          # integrator per key
        self.first = [0] * self.n        # time of first contact
        self.since = [0] * self.n        # time debounced press started
        self.presses = [0] * self.n      # statistics (test page)
        self.raw = 0
        self.live = 0          # keys whose integrator is non-zero
        self.down = 0          # debounced
        self.stuck = 0
        self.ambiguous = 0
        self.active = 0        # down, not stuck, not ambiguous
        self.fault = False
        self.scans = 0
        self.events = []
        self.apply_settings()

    def apply_settings(self):
        s = self.s
        self.on_n = max(2, s["debounce_ms"] // s["scan_ms"])
        self.settle = s["settle_us"]
        self.ghost_filter = s["ghost_filter"]
        self.stuck_ms = s["stuck_ms"]

    def scan_raw(self):
        mask = 0
        ncols = self.ncols
        settle = self.settle
        rows = self.rows
        for c, col in enumerate(self.cols):
            col.value(0)
            if settle:
                sleep_us(settle)
            for r, row in enumerate(rows):
                if not row.value():
                    mask |= 1 << (r * ncols + c)
            col.value(1)
        return mask

    def step(self, now):
        """Scan once. Returns a list of (key, time_of_first_contact) for keys
        newly confirmed as pressed. The list is reused between calls."""
        raw = self.scan_raw()
        self.raw = raw
        self.scans += 1
        events = self.events
        del events[:]
        if not raw and not self.live:
            # idle fast path: nothing pressed, nothing settling
            self.down = self.stuck = self.ambiguous = self.active = 0
            self.fault = False
            return events

        cnt, first, on_n = self.cnt, self.first, self.on_n
        down = self.down
        live = self.live
        check = raw | live
        for k in range(self.n):
            bit = 1 << k
            if not check & bit:
                continue
            if raw & bit:
                c = cnt[k]
                if c < on_n:
                    if c == 0:
                        first[k] = now
                    cnt[k] = c + 1
                    live |= bit
                    if c + 1 >= on_n:
                        down |= bit
                        self.since[k] = now
            else:
                cnt[k] -= 1
                if cnt[k] == 0:
                    down &= ~bit
                    live &= ~bit
        self.down = down
        self.live = live

        # stuck keys
        stuck = self.stuck & down
        if down:
            for k in range(self.n):
                bit = 1 << k
                if down & bit and not stuck & bit and ticks_diff(now, self.since[k]) > self.stuck_ms:
                    stuck |= bit
        self.stuck = stuck

        usable = down & ~stuck
        # ghost / ambiguity: a key is trusted only if it is alone in its row or column
        ambiguous = 0
        if self.ghost_filter and usable & (usable - 1):
            for k in range(self.n):
                bit = 1 << k
                if usable & bit:
                    r, c = divmod(k, self.ncols)
                    if popcount(usable & self.row_masks[r]) > 1 and popcount(usable & self.col_masks[c]) > 1:
                        ambiguous |= bit
        self.ambiguous = ambiguous
        self.fault = popcount(down) > NOISE_LIMIT
        active = 0 if self.fault else usable & ~ambiguous

        new = active & ~self.active
        if new:
            for k in range(self.n):
                if new & (1 << k):
                    self.presses[k] += 1
                    events.append((k, first[k]))
        self.active = active
        return events

    def clear_stats(self):
        for k in range(self.n):
            self.presses[k] = 0
