import machine
import asyncio
import utime


from config import *
from keypad import KeyPad
from led import LedManager
from log import NeoLogger
from Enow import EspNowRemoteControler
from game import GameManager

Logger = NeoLogger()
Logger.syncBlink(3, "green")

gamestatus = "waiting"
game_task = None  # Track the running game task


remote_controller = EspNowRemoteControler()
Key_Pad = KeyPad(row_pins, column_pins, keys)
Led_manager = LedManager(LED_row_pins, LED_column_pins, keys)

gameManager = GameManager(Key_Pad, Led_manager, remote_controller)

def _game_done(task):
    """Surface exceptions of the background game task and make sure LEDs end up off."""
    global game_task
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        exc = None
    except Exception:
        exc = None
    if exc:
        print("Game task crashed:", repr(exc))
        Led_manager.clear()
        gameManager.gameActive = False
    if game_task is task:
        game_task = None


def gameRunning():
    return game_task is not None and not game_task.done()


async def handleStart():
    global game_task

    # Ignore START while a game is already running
    if gameRunning():
        print("Game already running, START ignored")
        return

    await asyncio.gather(
        Logger.blink(5, "green", 0.2),
        remote_controller.sendMessage(START_MESSAGE)
    )
    Led_manager.clear()
    game_task = asyncio.create_task(gameManager.start())
    game_task.add_done_callback(_game_done)
    print("Game started as background task")


async def handleDemo():
    global game_task

    if gameRunning():
        print("Game already running, DEMO ignored")
        return

    await asyncio.gather(
        Logger.blink(5, "blue", 0.2),
        remote_controller.sendMessage(MODE_MESSAGE)
    )
    Led_manager.clear()
    game_task = asyncio.create_task(gameManager.startDemo())
    game_task.add_done_callback(_game_done)
    print("Demo started as background task")


async def handleStop():
    global game_task

    # Stop the game first, then notify (blink + message in parallel)
    task = game_task
    if task is not None and not task.done():
        print("Cancelling game task...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            print("Game task cancelled successfully")
        except Exception as err:
            print("Game task error on cancel:", repr(err))
    game_task = None

    Led_manager.clear()
    await asyncio.gather(
        Logger.blink(5, "purple", 0.2),
        remote_controller.sendMessage(STOP_MESSAGE)
    )
    # reset() sends ENDGAME_RESET if a game was still active
    await gameManager.reset()


async def remoteControllerMessageHandler(msg, mac):
    global gamestatus
    print("Handling message from", mac.hex(), ":", msg)

    if msg == START_MESSAGE:
        gamestatus = START_MESSAGE
        await handleStart()

    elif msg == MODE_MESSAGE:
        gamestatus = MODE_MESSAGE
        await handleDemo()

    elif msg == STOP_MESSAGE:
        gamestatus = STOP_MESSAGE
        await handleStop()

    # INIT (display handshake) and unknown messages are ignored


try:
    print("Starting game manager...")


    # Diagnostic: a key held at boot is reported by blinking its number
    # (bounded so a stuck key can't hang the boot forever)
    key_pressed = Key_Pad.read_keypad()
    for _ in range(10):
        if key_pressed is None:
            break
        print("pre-log key pressed:", key_pressed)
        Logger.syncBlink(int(key_pressed), "red")
        utime.sleep_ms(2500)
        key_pressed = Key_Pad.read_keypad()

    print("ledclear")
    Led_manager.clear()

    asyncio.run(remote_controller.messageReceiver(remoteControllerMessageHandler))

except KeyboardInterrupt:
    print("Stopping transceiver...")
    Led_manager.clear()
    remote_controller.close()
except Exception as err:
    # Unrecoverable error: show it on the status LED and reboot instead of hanging
    print("Fatal error:", repr(err))
    Led_manager.clear()
    Logger.syncBlink(5, "red", 200)
    machine.reset()





