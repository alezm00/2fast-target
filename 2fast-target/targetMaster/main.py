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


# print("cols:", str([i.value() for i in column_pins]))
# print("rows:", str([i.value() for i in row_pins]))

# connection_established = False
# def remoteControllerConnectionCallback(msg, mac):
#     print("Connection callback message:", msg)
#     global connection_established
#     if msg == INIT_MESSAGE:
#         connection_established = True
#         print("Connection established with remote controller.")
#         asyncio.create_task(Logger.blink(2, "yellow", 0.3))
#         return True

# def remoteControllerConnection():
#     global connection_established
#     asyncio.create_task(RemoteControler.messageReceiver(remoteControllerConnectionCallback))
#     while not connection_established:
#         print("Waiting for connection... Sending INIT message.")
#         asyncio.run(RemoteControler.sendMessage(INIT_MESSAGE))
#         utime.sleep_ms(1000)



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

    gameManager = GameManager(KeyPad, LedManager, RemoteController)
    asyncio.run(RemoteController.messageReceiver(remoteControllerMessageHandler))

except KeyboardInterrupt:
    print("Stopping transceiver...")
    RemoteController.close()





