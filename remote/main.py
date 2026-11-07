"""2Fast Target - radio remote (ESP32, MicroPython)."""
import time
import machine
import network
import espnow
import urandom

import config

BROADCAST = b"\xff\xff\xff\xff\xff\xff"


def pin_in(n):
    return machine.Pin(n, machine.Pin.IN, machine.Pin.PULL_UP) if n is not None else None


start_btn = pin_in(config.START_PIN)
stop_btn = pin_in(config.STOP_PIN)
led = machine.Pin(config.LED_PIN, machine.Pin.OUT) if config.LED_PIN is not None else None


def blink(times, ms=60):
    if led is None:
        return
    for _ in range(times):
        led.value(1)
        time.sleep_ms(ms)
        led.value(0)
        time.sleep_ms(ms)


def setup():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.config(channel=config.CHANNEL)
    sta.disconnect()
    e = espnow.ESPNow()
    e.active(True)
    e.add_peer(BROADCAST)
    return e


def send(e, cmd):
    # one random id per press: the master drops the repeated copies
    msg = "2FT|%s|%08x|%s" % (config.SECRET, urandom.getrandbits(30), cmd)
    ok = False
    for _ in range(config.REPEATS):
        try:
            ok = e.send(BROADCAST, msg) or ok
        except OSError as err:
            print("send error:", err)
        time.sleep_ms(15)
    blink(1 if ok else 4, 60 if ok else 40)
    print("sent", cmd, ok)


def pressed(pin, state):
    """Debounced falling edge detector. state = [stable_level, count]."""
    level = pin.value()
    if level == state[0]:
        state[1] = 0
        return False
    state[1] += 1
    if state[1] >= 4:
        state[0] = level
        state[1] = 0
        return level == 0
    return False


def run():
    e = setup()
    wdt = machine.WDT(timeout=10000)
    s_start, s_stop = [1, 0], [1, 0]
    blink(3)
    last = time.ticks_ms() - config.LOCKOUT_MS
    while True:
        wdt.feed()
        if time.ticks_diff(time.ticks_ms(), last) >= config.LOCKOUT_MS:
            if start_btn and pressed(start_btn, s_start):
                send(e, ("START:" + config.START_MODE) if config.START_MODE else "TOGGLE")
                last = time.ticks_ms()
            elif stop_btn and pressed(stop_btn, s_stop):
                send(e, "STOP")
                last = time.ticks_ms()
        time.sleep_ms(10)


try:
    run()
except KeyboardInterrupt:
    pass
except Exception as err:
    print("fatal:", repr(err))
    time.sleep(3)
    machine.reset()
