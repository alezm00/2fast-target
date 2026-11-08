import json
import os
import tempfile
import unittest

import fakehw
from fakehw import CLOCK, MATRIX
import config
import games
from settings import Settings
from scoreboard import Scoreboard
from session import Session


def params(**over):
    s = Settings("/nonexistent.json")
    p = dict(s.v)
    p.update(over)
    return p


ALL = list(range(25))


class GameTests(unittest.TestCase):
    def setUp(self):
        CLOCK.set(1000)

    def lit_target(self, g):
        self.assertEqual(bin(g.lit).count("1"), 1)
        return g.lit.bit_length() - 1

    def test_sequence_full_run_timing(self):
        g = games.create("sequence", ALL, params())
        g.begin(1000)
        t = 1000
        seen = []
        while not g.done:
            tgt = self.lit_target(g)
            seen.append(tgt)
            t += 200
            g.hit(tgt, t)
        self.assertEqual(sorted(seen), ALL)             # each target exactly once
        r = g.result(t)
        self.assertEqual((r["hits"], r["miss"], r["err"]), (25, 0, 0))
        self.assertEqual(r["total"], 25 * 200)
        self.assertEqual(sum(r["rt"]), r["total"])      # splits add up to the total
        self.assertEqual(r["avg"], 200)

    def test_sequence_wrong_hit_and_penalty(self):
        g = games.create("sequence", [1, 2, 3], params(seq_wrong_penalty_ms=500))
        g.begin(0)
        wrong = [x for x in (1, 2, 3) if x != self.lit_target(g)][0]
        g.hit(wrong, 100)
        self.assertEqual((g.errors, g.penalty), (1, 500))
        self.assertEqual(g.elapsed(1000), 1500)

    def test_sequence_timeout_skips_and_counts_miss(self):
        g = games.create("sequence", [4, 5], params(seq_timeout_ms=1000, seq_miss_penalty_ms=250))
        g.begin(0)
        g.tick(1001)
        self.assertEqual(g.misses, 1)
        g.tick(2002)                 # last target also times out -> must finish, not crash
        self.assertTrue(g.done)
        self.assertEqual(g.misses, 2)
        self.assertEqual(g.result(2002)["total"], 2002 + 500)

    def test_demo_is_endless(self):
        g = games.create("demo", [1, 2], params(demo_timeout_ms=300))
        g.begin(0)
        t = 0
        for _ in range(60):
            t += 100
            g.tick(t)
        self.assertFalse(g.done)

    def test_reflex_false_start_and_reaction(self):
        g = games.create("reflex", ALL, params(reflex_rounds=2, reflex_min_delay_ms=500, reflex_max_delay_ms=500))
        g.begin(0)
        self.assertEqual(g.lit, 0)
        g.hit(3, 100)                                    # before anything is lit
        self.assertEqual(g.errors, 1)
        g.tick(500)
        tgt = self.lit_target(g)
        g.hit(tgt, 650)
        self.assertEqual(g.rt, [150])
        self.assertEqual(g.lit, 0)                       # waiting again
        g.tick(1200); g.tick(1210)
        tgt = self.lit_target(g)
        g.hit(tgt, 1400)
        self.assertTrue(g.done)
        self.assertEqual(g.result(1400)["hits"], 2)

    def test_reflex_never_repeats_target(self):
        g = games.create("reflex", ALL, params(reflex_rounds=50, reflex_min_delay_ms=0, reflex_max_delay_ms=0))
        g.begin(0)
        last, t = None, 0
        while not g.done:
            t += 10
            g.tick(t)
            if g.lit:
                tgt = self.lit_target(g)
                self.assertNotEqual(tgt, last)
                last = tgt
                g.hit(tgt, t + 5)

    def test_timed_counts_hits_and_ends_on_time(self):
        g = games.create("timed", ALL, params(timed_duration_s=5))
        g.begin(0)
        t = 0
        while t < 4000:
            t += 100
            g.hit(self.lit_target(g), t)
        self.assertEqual(g.hits, 40)
        g.tick(5000)
        self.assertTrue(g.done)
        self.assertEqual(g.result(5000)["total"], 5000)
        g.hit(0, 5100)                                   # late hit is ignored
        self.assertEqual(g.hits, 40)

    def test_multi_lights_k_targets_and_finishes(self):
        g = games.create("multi", list(range(8)), params(multi_simultaneous=3, multi_timeout_ms=0))
        g.begin(0)
        self.assertEqual(bin(g.lit).count("1"), 3)
        t = 0
        while not g.done:
            t += 50
            tgt = (g.lit & -g.lit).bit_length() - 1
            g.hit(tgt, t)
            self.assertLessEqual(bin(g.lit).count("1"), 3)
        self.assertEqual(g.hits, 8)
        g2 = games.create("multi", list(range(8)), params(multi_simultaneous=3, multi_timeout_ms=0))
        g2.begin(0)
        off = [i for i in range(8) if not g2.lit >> i & 1][0]
        g2.hit(off, 10)
        self.assertEqual(g2.errors, 1)

    def test_multi_timeouts_finish_game(self):
        g = games.create("multi", [0, 1, 2, 3], params(multi_simultaneous=2, multi_timeout_ms=1000))
        g.begin(0)
        t = 0
        for _ in range(100):
            t += 100
            g.tick(t)
        self.assertTrue(g.done)
        self.assertEqual(g.misses, 4)

    def test_works_across_tick_counter_wrap(self):
        start = (1 << 30) - 500
        g = games.create("sequence", [1, 2], params())
        g.begin(start)
        tgt = self.lit_target(g)
        t = fakehw.time.ticks_add(start, 700)
        g.hit(tgt, t)
        self.assertEqual(g.rt, [700])


class SessionTests(unittest.TestCase):
    def setUp(self):
        CLOCK.set(0)
        self.tmp = tempfile.mkdtemp()
        self.s = Settings(os.path.join(self.tmp, "s.json"))
        self.b = Scoreboard(os.path.join(self.tmp, "r.json"))
        self.sess = Session(self.s, self.b)

    def advance(self, ms, step=10):
        for _ in range(ms // step):
            CLOCK.advance(step)
            self.sess.tick(CLOCK.now())

    def test_countdown_then_go(self):
        self.s.update({"countdown_step_ms": 100, "countdown_rand_ms": 0}, persist=False)
        ok, _ = self.sess.start("sequence", CLOCK.now())
        self.assertTrue(ok)
        self.assertEqual(self.sess.phase, "countdown")
        self.assertEqual(self.sess.out, 0b11111)          # first row lit
        self.advance(250)
        self.assertEqual(self.sess.out, (1 << 15) - 1)    # three rows
        self.advance(600)
        self.assertEqual(self.sess.phase, "running")
        self.assertEqual(bin(self.sess.out).count("1"), 1)

    def test_no_countdown(self):
        self.s.update({"countdown_enabled": False}, persist=False)
        self.sess.start("sequence", CLOCK.now())
        self.assertEqual(self.sess.phase, "running")

    def test_cannot_start_twice_and_stop_in_countdown(self):
        self.sess.start("sequence", CLOCK.now())
        ok, msg = self.sess.start("reflex", CLOCK.now())
        self.assertFalse(ok)
        self.assertTrue(self.sess.stop(CLOCK.now()))
        self.assertEqual((self.sess.phase, self.sess.out), ("idle", 0))

    def test_full_game_records_result_and_best(self):
        self.s.update({"countdown_enabled": False, "finish_blink": False}, persist=False)
        self.sess.start("sequence", CLOCK.now())
        while self.sess.phase == "running":
            CLOCK.advance(150)
            self.sess.hit(self.sess.out.bit_length() - 1, CLOCK.now())
        self.assertEqual(self.sess.phase, "finished")
        self.assertEqual(self.sess.result["total"], 25 * 150)
        self.assertTrue(self.sess.record)
        self.assertEqual(self.b.best["sequence"]["v"], 3750)
        # a slower game is not a record
        self.sess.start("sequence", CLOCK.now())
        while self.sess.phase == "running":
            CLOCK.advance(300)
            self.sess.hit(self.sess.out.bit_length() - 1, CLOCK.now())
        self.assertFalse(self.sess.record)
        self.assertEqual(len(self.b.recent), 2)

    def test_abort_keeps_time_but_is_not_recorded(self):
        self.s.update({"countdown_enabled": False}, persist=False)
        self.sess.start("sequence", CLOCK.now())
        CLOCK.advance(1234)
        self.sess.stop(CLOCK.now())
        self.assertTrue(self.sess.result["aborted"])
        self.assertEqual(self.sess.result["total"], 1234)
        self.assertEqual(self.b.recent, [])

    def test_disabled_targets_are_skipped(self):
        en = [i % 2 == 0 for i in range(25)]
        self.s.update({"enabled": en, "countdown_enabled": False}, persist=False)
        self.sess.start("sequence", CLOCK.now())
        seen = set()
        while self.sess.phase == "running":
            t = self.sess.out.bit_length() - 1
            seen.add(t)
            CLOCK.advance(10)
            self.sess.hit(t, CLOCK.now())
        self.assertEqual(seen, set(i for i in range(25) if i % 2 == 0))

    def test_start_without_mode_uses_the_selected_game_and_saved_params(self):
        self.s.update({"default_mode": "timed", "timed_duration_s": 7, "countdown_enabled": False}, persist=False)
        ok, _ = self.sess.start(None, CLOCK.now())
        self.assertTrue(ok)
        self.assertEqual((self.sess.mode, self.sess.game.id, self.sess.game.duration), ("timed", "timed", 7000))

    def test_unknown_mode_rejected(self):
        ok, msg = self.sess.start("zzz", CLOCK.now())
        self.assertFalse(ok)


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "s.json")

    def test_roundtrip_and_validation(self):
        s = Settings(self.path)
        changed, errors = s.update({"seq_timeout_ms": 3000, "ghost_filter": False})
        self.assertEqual((sorted(changed), errors), (["ghost_filter", "seq_timeout_ms"], {}))
        s2 = Settings(self.path)
        self.assertTrue(s2.load())
        self.assertEqual((s2["seq_timeout_ms"], s2["ghost_filter"]), (3000, False))

    def test_rejects_bad_values_atomically(self):
        s = Settings(self.path)
        changed, errors = s.update({"seq_timeout_ms": 10, "debounce_ms": 5})
        self.assertIn("seq_timeout_ms", errors)
        self.assertEqual(s["debounce_ms"], 8)             # nothing applied
        for bad in ({"scan_ms": "x"}, {"scan_ms": 1.5}, {"scan_ms": True}, {"nope": 1},
                    {"ap_password": "short"}, {"default_mode": "zzz"}, {"reflex_min_delay_ms": 9000},
                    {"keymap": [0] * 25}, {"enabled": [False] * 25}):
            self.assertTrue(s.update(bad)[1], bad)

    def test_corrupt_file_falls_back_to_defaults(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        s = Settings(self.path)
        self.assertFalse(s.load())
        self.assertEqual(s["seq_timeout_ms"], 5000)
        with open(self.path, "w") as f:
            json.dump({"seq_timeout_ms": "garbage", "debounce_ms": 12, "keymap": [1, 2]}, f)
        s.load()
        self.assertEqual((s["seq_timeout_ms"], s["debounce_ms"], s.keymap), (5000, 12, list(range(25))))

    def test_keymap_inverse(self):
        s = Settings(self.path)
        km = list(range(25))
        km[0], km[1] = 1, 0
        s.update({"keymap": km}, persist=False)
        inv = s.key_to_target()
        self.assertEqual((inv[1], inv[0]), (0, 1))


if __name__ == "__main__":
    unittest.main()
