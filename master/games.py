"""Game modes. Every mode is a small state machine driven by:

    begin(now)         the "go" instant, t0 of all timings
    hit(target, t)     a confirmed target press (t = time of first contact)
    tick(now)          periodic, handles timeouts / delays

Timing is always computed: total time, per-target reaction times, penalties.
`lit` is the bitmask of targets that must currently be lit.
"""
import random
from time import ticks_diff, ticks_add

from config import N

MODES = (
    ("sequence", "Sequenza",
     "Tutti i bersagli in ordine casuale, uno alla volta. Vince il tempo totale più basso.",
     ("seq_timeout_ms", "seq_wrong_penalty_ms", "seq_miss_penalty_ms")),
    ("reflex", "Riflessi",
     "Il bersaglio si accende dopo un'attesa casuale: misura il tempo di reazione.",
     ("reflex_rounds", "reflex_timeout_ms", "reflex_min_delay_ms", "reflex_max_delay_ms")),
    ("timed", "A tempo",
     "Colpisci più bersagli possibile entro il tempo limite.",
     ("timed_duration_s", "timed_timeout_ms")),
    ("multi", "Multi-bersaglio",
     "Più bersagli accesi insieme, colpiscili in qualsiasi ordine.",
     ("multi_simultaneous", "multi_timeout_ms")),
    ("demo", "Demo",
     "Sequenza infinita senza punteggio, per esposizione e prove.",
     ("demo_timeout_ms",)),
)
MODE_IDS = tuple(m[0] for m in MODES)


def shuffled(items):
    items = list(items)
    for i in range(len(items) - 1, 0, -1):
        j = random.randrange(i + 1)
        items[i], items[j] = items[j], items[i]
    return items


def pick_other(pool, last):
    """Random element of pool, different from `last` when possible."""
    if len(pool) > 1 and last in pool:
        while True:
            t = random.choice(pool)
            if t != last:
                return t
    return random.choice(pool)


class Game:
    id = ""
    endless = False

    def __init__(self, targets, p):
        self.targets = list(targets)   # enabled target indices
        self.p = p
        self.done = False
        self.lit = 0
        self.t0 = 0
        self.t_end = None
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.penalty = 0
        self.rt = []                    # reaction times of hits, in order
        self.tt = {}                    # target -> last reaction time
        self.hit_mask = 0
        self.miss_mask = 0
        self.total = len(self.targets)  # targets / rounds planned (0 = n.a.)

    # ---- interface ----------------------------------------------------------
    def begin(self, now):
        self.t0 = now

    def hit(self, target, t):
        pass

    def tick(self, now):
        pass

    # ---- helpers ------------------------------------------------------------
    def _register_hit(self, target, t, lit_t):
        ms = max(0, ticks_diff(t, lit_t))
        self.hits += 1
        self.rt.append(ms)
        self.tt[target] = ms
        self.hit_mask |= 1 << target
        return ms

    def _finish(self, t):
        self.done = True
        self.t_end = t
        self.lit = 0

    def elapsed(self, now):
        end = self.t_end if self.t_end is not None else now
        return max(0, ticks_diff(end, self.t0)) + self.penalty

    def remaining_ms(self, now):
        return None

    def progress(self):
        return self.hits + self.misses

    def result(self, now, aborted=False):
        rt = self.rt
        return {
            "mode": self.id,
            "total": self.elapsed(now),
            "hits": self.hits,
            "miss": self.misses,
            "err": self.errors,
            "pen": self.penalty,
            "avg": (sum(rt) // len(rt)) if rt else None,
            "best": min(rt) if rt else None,
            "worst": max(rt) if rt else None,
            "rt": rt,
            "tt": [self.tt.get(i, -1) for i in range(N)],
            "aborted": aborted,
            "endless": self.endless,
        }


class Sequence(Game):
    """Original game: every target once, random order, one lit at a time."""
    id = "sequence"

    def __init__(self, targets, p, loop=False):
        Game.__init__(self, targets, p)
        self.timeout = p["demo_timeout_ms" if loop else "seq_timeout_ms"]
        self.wrong_pen = 0 if loop else p["seq_wrong_penalty_ms"]
        self.miss_pen = 0 if loop else p["seq_miss_penalty_ms"]
        self.loop = loop
        self.endless = loop
        if loop:
            self.id = "demo"
        self.order = shuffled(self.targets)
        self.idx = 0
        self.lit_t = 0
        self.pause_until = None

    def begin(self, now):
        Game.begin(self, now)
        self._show(now)

    def _show(self, t):
        self.lit_t = t
        self.lit = 1 << self.order[self.idx]

    def _advance(self, t):
        self.idx += 1
        if self.idx >= len(self.order):
            if self.loop:
                self.order = shuffled(self.targets)
                self.idx = 0
                self.lit = 0
                self.hit_mask = 0
                self.pause_until = ticks_add(t, 1000)
                return
            self._finish(t)
            return
        self._show(t)

    def hit(self, target, t):
        if self.done or self.pause_until is not None:
            return
        if target == self.order[self.idx]:
            self._register_hit(target, t, self.lit_t)
            self._advance(t)
        else:
            self.errors += 1
            self.penalty += self.wrong_pen

    def tick(self, now):
        if self.done:
            return
        if self.pause_until is not None:
            if ticks_diff(now, self.pause_until) >= 0:
                self.pause_until = None
                self._show(now)
            return
        if ticks_diff(now, self.lit_t) > self.timeout:
            self.misses += 1
            self.penalty += self.miss_pen
            self.miss_mask |= self.lit
            self._advance(now)

    def remaining_ms(self, now):
        if self.done or self.pause_until is not None:
            return None
        return max(0, self.timeout - ticks_diff(now, self.lit_t))

    def progress(self):
        return self.idx


class Reflex(Game):
    """Reaction test: wait a random time, a target lights up, hit it."""
    id = "reflex"

    def __init__(self, targets, p):
        Game.__init__(self, targets, p)
        self.rounds = p["reflex_rounds"]
        self.total = self.rounds
        self.timeout = p["reflex_timeout_ms"]
        self.dmin = p["reflex_min_delay_ms"]
        self.dmax = max(p["reflex_max_delay_ms"], self.dmin)
        self.round = 0
        self.target = None
        self.last = None
        self.show_at = 0
        self.lit_t = 0

    def begin(self, now):
        Game.begin(self, now)
        self._schedule(now)

    def _schedule(self, t):
        self.lit = 0
        self.target = pick_other(self.targets, self.last)
        self.last = self.target
        self.show_at = ticks_add(t, random.randint(self.dmin, self.dmax))

    def _next_round(self, t):
        self.round += 1
        if self.round >= self.rounds:
            self._finish(t)
        else:
            self._schedule(t)

    def hit(self, target, t):
        if self.done:
            return
        if self.lit and target == self.target:
            self._register_hit(target, t, self.lit_t)
            self._next_round(t)
        else:
            # pressed too early, or the wrong target
            self.errors += 1

    def tick(self, now):
        if self.done:
            return
        if not self.lit:
            if ticks_diff(now, self.show_at) >= 0:
                self.lit = 1 << self.target
                self.lit_t = now
        elif ticks_diff(now, self.lit_t) > self.timeout:
            self.misses += 1
            self.miss_mask |= self.lit
            self._next_round(now)

    def remaining_ms(self, now):
        if self.done or not self.lit:
            return None
        return max(0, self.timeout - ticks_diff(now, self.lit_t))

    def progress(self):
        return self.round


class Timed(Game):
    """As many hits as possible before time runs out."""
    id = "timed"

    def __init__(self, targets, p):
        Game.__init__(self, targets, p)
        self.duration = p["timed_duration_s"] * 1000
        self.timeout = p["timed_timeout_ms"]
        self.total = 0
        self.target = None
        self.lit_t = 0

    def begin(self, now):
        Game.begin(self, now)
        self._show(now)

    def _show(self, t):
        self.target = pick_other(self.targets, self.target)
        self.lit = 1 << self.target
        self.lit_t = t

    def hit(self, target, t):
        if self.done:
            return
        if ticks_diff(t, self.t0) > self.duration:
            return  # too late, tick() will close the game
        if target == self.target:
            self._register_hit(target, t, self.lit_t)
            self._show(t)
        else:
            self.errors += 1

    def tick(self, now):
        if self.done:
            return
        if ticks_diff(now, self.t0) >= self.duration:
            self._finish(ticks_add(self.t0, self.duration))
            return
        if self.timeout and ticks_diff(now, self.lit_t) > self.timeout:
            self.misses += 1
            self.miss_mask |= self.lit
            self._show(now)

    def remaining_ms(self, now):
        if self.done:
            return 0
        return max(0, self.duration - ticks_diff(now, self.t0))

    def progress(self):
        return self.hits


class Multi(Game):
    """Several targets lit at once, hit them in any order."""
    id = "multi"

    def __init__(self, targets, p):
        Game.__init__(self, targets, p)
        self.k = p["multi_simultaneous"]
        self.timeout = p["multi_timeout_ms"]
        self.pool = shuffled(self.targets)
        self.lit_t = {}
        self.done_count = 0
        self.checked = 0

    def begin(self, now):
        Game.begin(self, now)
        self._refill(now)

    def _refill(self, t):
        while self.pool and bin(self.lit).count("1") < self.k:
            target = self.pool.pop()
            self.lit |= 1 << target
            self.lit_t[target] = t
        if not self.lit and not self.pool:
            self._finish(t)

    def hit(self, target, t):
        if self.done:
            return
        if self.lit & (1 << target):
            self._register_hit(target, t, self.lit_t[target])
            self.lit &= ~(1 << target)
            self.done_count += 1
            self._refill(t)
        else:
            self.errors += 1

    def tick(self, now):
        if self.done or not self.timeout:
            return
        if ticks_diff(now, self.checked) < 20:
            return
        self.checked = now
        for target in list(self.lit_t):
            if self.lit & (1 << target) and ticks_diff(now, self.lit_t[target]) > self.timeout:
                self.lit &= ~(1 << target)
                self.misses += 1
                self.miss_mask |= 1 << target
                self.done_count += 1
        if not self.done:
            self._refill(now)

    def remaining_ms(self, now):
        if self.done or not self.timeout or not self.lit:
            return None
        oldest = min(self.lit_t[t] for t in self.lit_t if self.lit & (1 << t))
        return max(0, self.timeout - ticks_diff(now, oldest))

    def progress(self):
        return self.done_count


def create(mode, targets, params):
    if mode == "sequence":
        return Sequence(targets, params)
    if mode == "demo":
        return Sequence(targets, params, loop=True)
    if mode == "reflex":
        return Reflex(targets, params)
    if mode == "timed":
        return Timed(targets, params)
    if mode == "multi":
        return Multi(targets, params)
    raise ValueError("modalità sconosciuta")
