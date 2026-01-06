from machine import Pin
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


async def handleStart():
    global game_task

    # Run blink and send message together
    await asyncio.gather(
        Logger.blink(5, "green", 0.2),
        remote_controller.sendMessage(START_MESSAGE)
    )
    Led_manager.clear()
    # Start game as a background task if not already running
    if game_task is None or game_task.done():
        game_task = asyncio.create_task(gameManager.start())
        print("Game started as background task")

async def handleStop():
    global game_task

    # Run blink and send message together
    await asyncio.gather(
        Logger.blink(5, "purple", 0.2),
        remote_controller.sendMessage(STOP_MESSAGE)
    )

    # Cancel the game task if it's running
    if game_task and not game_task.done():
        print("Cancelling game task...")
        game_task.cancel()
        try:
            await game_task
        except asyncio.CancelledError:
            print("Game task cancelled successfully")
    # Call reset method
    await gameManager.reset()
    game_task = None

async def handleDemo():
    global game_task

    await asyncio.gather(
        Logger.blink(5, "blue", 0.2),
        remote_controller.sendMessage(MODE_MESSAGE)
    )
    Led_manager.clear()

    if game_task is None or game_task.done():
        game_task = asyncio.create_task(gameManager.startDemo())
        print("Game started as background task")



async def remoteControllerMessageHandler(msg, mac):
    global gamestatus
    print(f"Handling message from {mac.hex()}: {msg.decode()}")

    if msg == START_MESSAGE:
        gamestatus = START_MESSAGE
        print("Received START command from remote controller.")
        await handleStart()

    elif msg == MODE_MESSAGE:
        gamestatus = MODE_MESSAGE
        print("Received DEMO command from remote controller.")
        await handleDemo()

    elif msg == STOP_MESSAGE:
        gamestatus = STOP_MESSAGE
        print("Received STOP command from remote controller.")
        await handleStop()


try:
    print("Starting game manager...")

    key_pressed = Key_Pad.read_keypad()
    while key_pressed is not None:
        print(utime.time_ns(), "pre-log key pressed:", key_pressed)
        utime.sleep_ms(500)
        logTimes = int(key_pressed) if key_pressed is not None else 0
        Logger.syncBlink(logTimes, "red")
        utime.sleep_ms(10)
        key_pressed = Key_Pad.read_keypad()
    print("ledclear")
    Led_manager.clear()
   # utime.sleep_ms(5000)
   #
   # print("traffic")
   #
   # Led_manager.trafficLight()
   #
   # utime.sleep_ms(10000)
   # for i in range(25):
   #     print("blinking led: " + str(i))
   #     Led_manager.ledON(str(i))
   #     utime.sleep_ms(2000)
   #     Led_manager.ledOFF(str(i))
   #     utime.sleep_ms(1000)


    gameManager = GameManager(Key_Pad, Led_manager, remote_controller)
    asyncio.run(remote_controller.messageReceiver(remoteControllerMessageHandler))

except KeyboardInterrupt:
    print("Stopping transceiver...")
    remote_controller.close()





