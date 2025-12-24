from machine import Pin
import asyncio
import utime



from config import *
from keypad import KeyPad
from led import LedManager
from log import NeoLogger
from Enow import EspNowReemoteControler
from game import GameManager

Logger = NeoLogger()
Logger.syncBlink(3, "green")

gamestatus = "waiting"
game_task = None  # Track the running game task


RemoteController = EspNowReemoteControler()



async def handleStart():
    global game_task

    # Run blink and send message together
    await asyncio.gather(
        Logger.blink(5, "green", 0.2),
        RemoteController.sendMessage(START_MESSAGE)
    )

    # Start game as a background task if not already running
    if game_task is None or game_task.done():
        game_task = asyncio.create_task(gameManager.start())
        print("Game started as background task")

async def handleStop():
    global game_task

    # Run blink and send message together
    await asyncio.gather(
        Logger.blink(5, "purple", 0.2),
        RemoteController.sendMessage(STOP_MESSAGE)
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

async def remoteControllerMessageHandler(msg, mac):
    global gamestatus
    print(f"Handling message from {mac.hex()}: {msg.decode()}")

    if msg == START_MESSAGE:
        gamestatus = START_MESSAGE
        print("Received START command from remote controller.")
        await handleStart()

    elif msg == STOP_MESSAGE:
        gamestatus = STOP_MESSAGE
        print("Received STOP command from remote controller.")
        await handleStop()


try:
    print("Starting game manager...")


    KeyPad = KeyPad(row_pins, column_pins, keys)
    LedManager = LedManager(LED_row_pins, LED_column_pins, keys)

    while True:
        key_pressed = KeyPad.read_keypad()
        print(utime.time_ns(),"key pressed:", key_pressed)

        utime.sleep_ms(10)



    gameManager = GameManager(KeyPad, LedManager, RemoteController)
    asyncio.run(RemoteController.messageReceiver(remoteControllerMessageHandler))

except KeyboardInterrupt:
    print("Stopping transceiver...")
    RemoteController.close()





