"""2Fast Target - master firmware entry point."""
import asyncio
import gc
import sys

import machine

import config
from settings import Settings
from scoreboard import Scoreboard
from keypad import Keypad
from leds import LedMatrix, StatusLed
from app import App
from buttons import StartButton
import net
from webserver import WebServer


def reboot():
    machine.reset()


async def supervised(name, factory, delay_ms=2000):
    """Run a task forever: if it crashes, log it and restart it."""
    while True:
        try:
            await factory()
            return
        except asyncio.CancelledError:
            raise
        except Exception as err:
            print("task %s crashed: %r" % (name, err))
            try:
                sys.print_exception(err)
            except Exception:
                pass
            gc.collect()
            await asyncio.sleep_ms(delay_ms)


async def watchdog_feeder(wdt):
    while True:
        wdt.feed()
        await asyncio.sleep(1)


async def main():
    settings = Settings()
    settings.load()
    board = Scoreboard()
    board.load()

    status = StatusLed(config.STATUS_PIN)
    status.set(StatusLed.YELLOW)

    leds = LedMatrix(config.LED_ROW_PINS, config.LED_COL_PINS, config.LED_ACTIVE_LOW)
    keypad = Keypad(config.KEY_ROW_PINS, config.KEY_COL_PINS, settings)
    app = App(settings, keypad, leds, board, status)

    info = net.start_wifi(settings)
    web = WebServer(app, info, config.HTTP_PORT, "web", reboot)
    button = StartButton(app, config.BTN_START_PIN)

    tasks = [
        asyncio.create_task(app.run()),
        asyncio.create_task(supervised("web", web.serve)),
        asyncio.create_task(supervised("button", button.run)),
        asyncio.create_task(supervised("sta", lambda: net.sta_supervisor(info, settings), 10000)),
    ]
    if config.ENABLE_WDT:
        wdt = machine.WDT(timeout=config.WDT_TIMEOUT_MS)
        tasks.append(asyncio.create_task(watchdog_feeder(wdt)))
    print("2Fast Target %s ready" % config.VERSION)
    await asyncio.gather(*tasks)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("stopped")
except Exception as err:
    # unrecoverable: keep a trace, then reboot (5 s window to press Ctrl-C)
    try:
        sys.print_exception(err)
        with open("error.log", "w") as f:
            sys.print_exception(err, f)
    except Exception:
        pass
    import time
    time.sleep(5)
    machine.reset()
