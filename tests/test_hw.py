import unittest

import fakehw
from fakehw import CLOCK, MATRIX, press, release
import config
from settings import Settings
from keypad import Keypad
from leds import LedMatrix


def make_keypad(**over):
    s = Settings("/nonexistent.json")
    s.update(over, persist=False)
    return Keypad(config.KEY_ROW_PINS, config.KEY_COL_PINS, s), s


def run(kp, ms, step=2):
    """Scan for `ms` virtual milliseconds, collect events."""
    ev = []
    for _ in range(ms // step):
        CLOCK.advance(step)
        ev += list(kp.step(CLOCK.now()))
    return ev


class KeypadTests(unittest.TestCase):
    def setUp(self):
        MATRIX.reset()
        CLOCK.set(10_000)

    def test_single_press_has_first_contact_timestamp(self):
        kp, _ = make_keypad()
        run(kp, 20)
        t_press = CLOCK.now()
        press(7)
        ev = run(kp, 40)
        self.assertEqual([k for k, _ in ev], [7])
        # timestamp is the first contact, not the (later) debounce time
        self.assertLessEqual(fakehw.time.ticks_diff(ev[0][1], t_press), 4)

    def test_no_repeat_while_held_and_again_after_release(self):
        kp, _ = make_keypad()
        press(3)
        self.assertEqual(len(run(kp, 100)), 1)
        release(3)
        run(kp, 60)
        press(3)
        self.assertEqual(len(run(kp, 60)), 1)

    def test_glitch_is_ignored(self):
        kp, _ = make_keypad()
        press(12)
        run(kp, 2)          # a single scan of contact
        release(12)
        self.assertEqual(run(kp, 60), [])

    def test_bounce_gives_one_event(self):
        kp, _ = make_keypad()
        for _ in range(3):  # make/break chatter, then solid contact
            press(5); run(kp, 2); release(5); run(kp, 2)
        press(5)
        ev = run(kp, 60)
        self.assertEqual([k for k, _ in ev], [5])

    def test_ghost_key_is_not_reported(self):
        kp, _ = make_keypad()
        # keys 0 (r0c0), 1 (r0c1), 5 (r1c0) closed -> ghost at 6 (r1c1)
        press(0, 1, 5)
        ev = run(kp, 60)
        self.assertNotIn(6, [k for k, _ in ev])
        self.assertIn(6, [k for k in range(25) if kp.raw >> k & 1])  # the ghost really is on the raw scan

    def test_two_real_keys_in_a_row_are_both_accepted(self):
        kp, _ = make_keypad()
        press(0, 1)
        ev = run(kp, 60)
        self.assertEqual(sorted(k for k, _ in ev), [0, 1])

    def test_key_is_not_reported_twice_when_it_turns_ambiguous_and_clear(self):
        kp, _ = make_keypad()
        press(0, 1)
        ev = run(kp, 40)
        press(5)                 # 3 corners of a rectangle -> 0, 1, 5 (and ghost 6) ambiguous
        ev += run(kp, 40)
        release(0)               # ambiguity ends while 1 and 5 are still held
        ev += run(kp, 40)
        # each key exactly once; 5 is confirmed late, as soon as the ambiguity is gone
        self.assertEqual(sorted(k for k, _ in ev), [0, 1, 5])

    def test_ghost_filter_can_be_disabled(self):
        kp, _ = make_keypad(ghost_filter=False)
        press(0, 1, 5)
        ev = run(kp, 60)
        self.assertIn(6, [k for k, _ in ev])

    def test_stuck_key_masked_until_released(self):
        kp, _ = make_keypad(stuck_ms=500)
        press(9)
        self.assertEqual(len(run(kp, 100)), 1)
        run(kp, 600)
        self.assertTrue(kp.stuck >> 9 & 1)
        # other keys still work while 9 is stuck
        press(10)
        self.assertEqual([k for k, _ in run(kp, 60)], [10])
        release(9, 10)
        run(kp, 60)
        self.assertEqual(kp.stuck, 0)

    def test_noise_many_keys_ignored(self):
        kp, _ = make_keypad()
        press(*range(0, 20))
        ev = run(kp, 60)
        self.assertEqual(ev, [])
        self.assertTrue(kp.fault)

    def test_idle_fast_path(self):
        kp, _ = make_keypad()
        self.assertEqual(run(kp, 100), [])
        self.assertEqual((kp.down, kp.live, kp.active), (0, 0, 0))


class LedTests(unittest.TestCase):
    def setUp(self):
        MATRIX.reset()

    def sample(self, leds, steps=40):
        seen, union = [], set()
        for _ in range(steps):
            leds.step()
            lit = MATRIX.lit()
            seen.append(lit)
            union |= lit
        return seen, union

    def test_single_led_static(self):
        leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
        leds.on(13)
        seen, union = self.sample(leds)
        self.assertTrue(all(s == {13} for s in seen))

    def test_multiple_leds_never_light_extras(self):
        leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
        want = {0, 7, 12, 18, 24, 3}
        leds.set(sum(1 << i for i in want))
        seen, union = self.sample(leds, 60)
        self.assertEqual(union, want)                     # all of them shown
        self.assertTrue(all(s <= want for s in seen))     # and nothing else, ever

    def test_row_is_a_single_group(self):
        leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
        leds.set(0b11111 << 10)
        seen, _ = self.sample(leds, 10)
        self.assertTrue(all(s == set(range(10, 15)) for s in seen))

    def test_clear(self):
        leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
        leds.set((1 << 25) - 1)
        self.sample(leds)
        leds.clear()
        seen, union = self.sample(leds, 5)
        self.assertEqual(union, set())


if __name__ == "__main__":
    unittest.main()
