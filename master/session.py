"""One game session: countdown -> running -> finished, with timing."""
import random
from time import ticks_diff, ticks_add, ticks_ms

import games
from config import ROWS, COLS

IDLE, COUNTDOWN, RUNNING, FINISHED = "idle", "countdown", "running", "finished"

BLINK_MS = 100
BLINK_TIMES = 4


class Session:
    def __init__(self, settings, scoreboard):
        self.settings = settings
        self.board = scoreboard
        self.phase = IDLE
        self.mode = settings["default_mode"]
        self.game = None
        self.out = 0              # LED mask requested by the session
        self.result = None        # last result (dict) or None
        self.rid = 0              # increments for each new result
        self.record = False
        self.cd_rows = 0
        self.cd_next = 0
        self.cd_go = None
        self.blink_end = 0
        self.blink_t0 = 0

    # ---- control ----------------------------------------------------------
    def params_for(self, mode, overrides):
        """Settings merged with per-game overrides (only keys of that mode)."""
        p = dict(self.settings.v)
        if overrides:
            allowed = None
            for m in games.MODES:
                if m[0] == mode:
                    allowed = m[3]
            clean, errors = self.settings.validate(
                {k: v for k, v in overrides.items() if allowed and k in allowed})
            if errors:
                return None, errors
            p.update(clean)
        return p, {}

    def start(self, mode, overrides, now):
        if self.phase in (COUNTDOWN, RUNNING):
            return False, "Partita già in corso"
        if mode not in games.MODE_IDS:
            return False, "Modalità sconosciuta"
        targets = self.settings.enabled_targets()
        if not targets:
            return False, "Nessun bersaglio attivo"
        params, errors = self.params_for(mode, overrides)
        if errors:
            return False, "Parametri non validi: " + ", ".join(errors)
        if mode == "multi" and len(targets) < 2:
            return False, "Servono almeno 2 bersagli attivi"
        self.mode = mode
        self.game = games.create(mode, targets, params)
        self.result = None
        self.record = False
        self.blink_end = 0
        if self.settings["countdown_enabled"]:
            self.phase = COUNTDOWN
            self.cd_rows = 1
            self.cd_go = None
            self.cd_next = ticks_add(now, self.settings["countdown_step_ms"])
            self.out = self._rows_mask(1)
        else:
            self._go(now)
        return True, "ok"

    def stop(self, now):
        if self.phase == COUNTDOWN:
            self.phase = IDLE
            self.game = None
            self.out = 0
            return True
        if self.phase == RUNNING:
            self._finish(now, aborted=not self.game.endless)
            return True
        return False

    def active(self):
        return self.phase in (COUNTDOWN, RUNNING)

    # ---- internals ----------------------------------------------------------
    @staticmethod
    def _rows_mask(k):
        return (1 << (k * COLS)) - 1

    def _go(self, now):
        self.phase = RUNNING
        self.game.begin(now)
        self.out = self.game.lit

    def _finish(self, now, aborted):
        g = self.game
        res = g.result(now, aborted)
        self.phase = FINISHED
        self.out = 0
        if not aborted and not g.endless:
            n, self.record = self.board.record(res)
            res["n"] = n
        self.result = res
        self.rid += 1
        if not aborted and self.settings["finish_blink"]:
            self.blink_t0 = ticks_ms()
            self.blink_end = ticks_add(self.blink_t0, 2 * BLINK_MS * BLINK_TIMES)

    # ---- periodic -----------------------------------------------------------
    def hit(self, target, t):
        if self.phase == RUNNING:
            self.game.hit(target, t)
            self.out = self.game.lit
            if self.game.done:
                self._finish(self.game.t_end, False)

    def tick(self, now):
        ph = self.phase
        if ph == COUNTDOWN:
            if self.cd_go is not None:
                if ticks_diff(now, self.cd_go) >= 0:
                    self._go(now)
            elif ticks_diff(now, self.cd_next) >= 0:
                if self.cd_rows < ROWS:
                    self.cd_rows += 1
                    self.cd_next = ticks_add(now, self.settings["countdown_step_ms"])
                    self.out = self._rows_mask(self.cd_rows)
                else:
                    extra = self.settings["countdown_rand_ms"]
                    self.cd_go = ticks_add(now, random.randint(0, extra) if extra else 0)
        elif ph == RUNNING:
            self.game.tick(now)
            if self.game.done:
                self._finish(self.game.t_end, False)
            else:
                self.out = self.game.lit
        elif ph == FINISHED and self.blink_end:
            if ticks_diff(now, self.blink_end) >= 0:
                self.blink_end = 0
                self.out = 0
            else:
                phase = ticks_diff(now, self.blink_t0) // BLINK_MS
                self.out = (1 << (ROWS * COLS)) - 1 if phase % 2 == 0 else 0

    # ---- state for the UI -----------------------------------------------------
    def state(self, now):
        g = self.game
        ph = self.phase
        st = {"phase": ph, "mode": self.mode, "rid": self.rid}
        if g is None:
            st.update(el=0, lit=0, hit=0, miss_m=0, hits=0, miss=0, err=0, prog=0, total=0, rem=None)
            return st
        if ph == RUNNING:
            el = g.elapsed(now)
        elif ph == FINISHED and self.result:
            el = self.result["total"]
        else:
            el = 0
        st.update(
            el=el,
            lit=g.lit if ph == RUNNING else 0,
            hit=g.hit_mask,
            miss_m=g.miss_mask,
            hits=g.hits,
            miss=g.misses,
            err=g.errors,
            prog=g.progress(),
            total=g.total,
            rem=g.remaining_ms(now) if ph == RUNNING else None,
        )
        if ph == COUNTDOWN:
            st["cd"] = self.cd_rows
        if ph == FINISHED:
            st["record"] = self.record
        return st
