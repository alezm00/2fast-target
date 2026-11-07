"""Application core: ties keypad, LEDs, game session, test/calibration mode
and the command sources (web, local buttons, radio remote) together."""
import asyncio
import gc
from time import ticks_ms, ticks_diff

import config
from config import N, ROWS, COLS
from session import Session, IDLE, COUNTDOWN, RUNNING, FINISHED
from leds import StatusLed

PLAY, TEST, LEARN = "play", "test", "learn"


class App:
    def __init__(self, settings, keypad, leds, scoreboard, status=None):
        self.settings = settings
        self.keypad = keypad
        self.leds = leds
        self.board = scoreboard
        self.status = status or StatusLed(None)
        self.session = Session(settings, scoreboard)
        self.mode = PLAY
        self.k2t = settings.key_to_target()

        # test mode
        self.test_mask = 0
        self.pattern = None
        self.pattern_i = 0
        self.pattern_t = 0
        self.last_key = None      # (target, ticks) of last press

        # calibration wizard
        self.learn = None

        self.last_cmd = None      # (source, command, ticks)
        self.loops = 0
        self.loop_t = ticks_ms()
        self.loop_hz = 0
        self.boot_ms = ticks_ms()

    # ---- settings changes -------------------------------------------------
    def apply_settings(self):
        self.keypad.apply_settings()
        self.k2t = self.settings.key_to_target()

    # ---- commands (web / buttons / radio) ---------------------------------
    def note(self, source, cmd):
        self.last_cmd = (source, cmd, ticks_ms())

    def cmd_start(self, mode=None, overrides=None, source="web"):
        if self.mode != PLAY:
            return False, "Esci dalla modalità test per giocare"
        self.note(source, "start")
        return self.session.start(mode or self.session.mode, overrides, ticks_ms())

    def cmd_stop(self, source="web"):
        self.note(source, "stop")
        if self.mode != PLAY:
            return False, "Modalità test attiva"
        ok = self.session.stop(ticks_ms())
        return ok, "ok" if ok else "Nessuna partita in corso"

    def cmd_toggle(self, source="button"):
        if self.session.active():
            return self.cmd_stop(source)
        return self.cmd_start(None, None, source)

    def set_app_mode(self, mode):
        if mode not in (PLAY, TEST):
            return False, "Modalità non valida"
        if mode == TEST:
            self.session.stop(ticks_ms())
        self.mode = mode
        self.test_mask = 0
        self.pattern = None
        self.learn = None
        self.keypad.clear_stats()
        return True, "ok"

    # ---- test mode --------------------------------------------------------
    def test_set_led(self, i, on):
        if self.mode != TEST or not 0 <= i < N:
            return False
        self.pattern = None
        bit = 1 << i
        self.test_mask = (self.test_mask | bit) if on else (self.test_mask & ~bit)
        return True

    def test_set_mask(self, mask):
        if self.mode != TEST:
            return False
        self.pattern = None
        self.test_mask = mask & ((1 << N) - 1)
        return True

    def test_pattern(self, name):
        if self.mode != TEST:
            return False
        if name == "all":
            return self.test_set_mask((1 << N) - 1)
        if name == "none":
            return self.test_set_mask(0)
        if name in ("chase", "rows", "cols"):
            self.pattern = name
            self.pattern_i = 0
            self.pattern_t = 0
            return True
        return False

    def _pattern_step(self, now):
        if ticks_diff(now, self.pattern_t) < 0:
            return
        name, i = self.pattern, self.pattern_i
        if name == "chase":
            self.test_mask = 1 << i
            self.pattern_i = (i + 1) % N
            self.pattern_t = now + 200
        elif name == "rows":
            r = i % ROWS
            self.test_mask = sum(1 << (r * COLS + c) for c in range(COLS))
            self.pattern_i = i + 1
            self.pattern_t = now + 400
        else:
            c = i % COLS
            self.test_mask = sum(1 << (r * COLS + c) for r in range(ROWS))
            self.pattern_i = i + 1
            self.pattern_t = now + 400

    # ---- calibration wizard -----------------------------------------------
    def learn_cmd(self, action):
        """start | skip | back | cancel"""
        if action == "start":
            if self.mode == PLAY:
                self.set_app_mode(TEST)
            self.mode = LEARN
            self.pattern = None
            self.learn = {"i": 0, "map": [None] * N, "msg": "Premi il bersaglio acceso"}
            return True, "ok"
        if self.mode != LEARN or self.learn is None:
            return False, "Calibrazione non attiva"
        L = self.learn
        if action == "cancel":
            self.mode = TEST
            self.learn = None
            return True, "ok"
        if action == "skip":
            L["map"][L["i"]] = -1       # dead / missing target
            L["msg"] = "Bersaglio %d saltato (disattivato)" % L["i"]
            return self._learn_next()
        if action == "back":
            if L["i"] > 0:
                L["i"] -= 1
                L["map"][L["i"]] = None
                L["msg"] = "Ripeti il bersaglio %d" % L["i"]
            return True, "ok"
        return False, "Azione non valida"

    def _learn_next(self):
        L = self.learn
        L["i"] += 1
        if L["i"] < N:
            return True, "ok"
        # finished: fill skipped targets with the keys left over
        used = set(k for k in L["map"] if k is not None and k >= 0)
        free = [k for k in range(N) if k not in used]
        keymap, enabled = [], []
        for t in range(N):
            k = L["map"][t]
            if k is None or k < 0:
                keymap.append(free.pop(0))
                enabled.append(False)
            else:
                keymap.append(k)
                enabled.append(True)
        changed, errors = self.settings.update({"keymap": keymap, "enabled": enabled})
        if errors:
            L["i"] = N - 1
            L["msg"] = "Errore: " + ", ".join(errors.values())
            return False, L["msg"]
        self.apply_settings()
        self.mode = TEST
        self.learn = None
        return True, "ok"

    def _learn_key(self, key):
        L = self.learn
        if key in L["map"]:
            L["msg"] = "Tasto già assegnato al bersaglio %d" % L["map"].index(key)
            return
        L["map"][L["i"]] = key
        L["msg"] = "Bersaglio %d associato" % L["i"]
        self._learn_next()

    # ---- main loop --------------------------------------------------------
    def on_key(self, key, t, now):
        if self.mode == LEARN and self.learn:
            self._learn_key(key)
            return
        target = self.k2t[key]
        self.last_key = (target, now)
        if self.mode == PLAY and self.settings.enabled[target]:
            self.session.hit(target, t)

    def tick(self, now):
        if self.mode == PLAY:
            self.session.tick(now)
            self.leds.set(self.session.out)
            ph = self.session.phase
            self.status.set(
                StatusLed.BLUE if ph == RUNNING else
                StatusLed.YELLOW if ph == COUNTDOWN else
                StatusLed.PURPLE if ph == FINISHED else StatusLed.GREEN)
        elif self.mode == TEST:
            if self.pattern:
                self._pattern_step(now)
            self.leds.set(self.test_mask)
            self.status.set(StatusLed.YELLOW)
        else:  # LEARN
            if self.learn and self.learn["i"] < N:
                self.leds.set(1 << self.learn["i"])
            self.status.set(StatusLed.YELLOW)

    async def run(self):
        """Hardware loop: scan, game logic, LED refresh."""
        kp, leds = self.keypad, self.leds
        while True:
            now = ticks_ms()
            try:
                for key, t in kp.step(now):
                    self.on_key(key, t, now)
                self.tick(now)
                leds.step()
            except Exception as err:    # never let one bad frame stop the game hardware
                print("loop error:", repr(err))
            self.loops += 1
            if ticks_diff(now, self.loop_t) >= 1000:
                self.loop_hz = self.loops * 1000 // ticks_diff(now, self.loop_t)
                self.loops = 0
                self.loop_t = now
            await asyncio.sleep_ms(self.settings["scan_ms"])

    # ---- state for the UI ---------------------------------------------------
    def _to_target_mask(self, key_mask):
        out = 0
        if key_mask:
            inv = self.k2t
            for k in range(N):
                if key_mask & (1 << k):
                    out |= 1 << inv[k]
        return out

    def state(self):
        now = ticks_ms()
        st = self.session.state(now)
        st["app"] = self.mode
        if self.last_cmd:
            st["cmd"] = [self.last_cmd[0], self.last_cmd[1], ticks_diff(now, self.last_cmd[2])]
        if self.mode != PLAY:
            kp = self.keypad
            st["lit"] = self.leds.mask
            st["raw"] = self._to_target_mask(kp.raw)
            st["down"] = self._to_target_mask(kp.down)
            st["stuck"] = self._to_target_mask(kp.stuck)
            st["amb"] = self._to_target_mask(kp.ambiguous)
            st["fault"] = kp.fault
            st["hz"] = self.loop_hz
            pr = [0] * N
            for k in range(N):
                pr[self.k2t[k]] = kp.presses[k]
            st["presses"] = pr
            if self.last_key:
                st["last"] = self.last_key[0]
            if self.learn:
                st["learn"] = {"i": self.learn["i"], "msg": self.learn["msg"],
                               "done": sum(1 for x in self.learn["map"] if x is not None)}
        return st

    def free_mem(self):
        gc.collect()
        return gc.mem_free()
