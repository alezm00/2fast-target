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

RemoteControler = EspNowReemoteControler()


print("cols:", str([i.value() for i in column_pins]))
print("rows:", str([i.value() for i in row_pins]))
KeyPad = KeyPad(row_pins, column_pins, keys)
LedManager = LedManager(LED_row_pins, LED_column_pins, keys)





gameManager = GameManager(KeyPad, LedManager)




# gameManager.start()

connection_established = False
def remoteControllerConnectionCallback(msg, mac):
    global connection_established
    if msg == INIT_MESSAGE:
        connection_established = True
        print("Connection established with remote controller.")
        asyncio.create_task(Logger.blink(5, "yellow", 0.3))
        return True


def remoteControllerConnection():
    global connection_established
    asyncio.create_task(RemoteControler.messageReceiver(remoteControllerConnectionCallback))
    while not connection_established:
        print("Waiting for connection... Sending INIT message.")
        asyncio.run(RemoteControler.sendMessage(INIT_MESSAGE))
        utime.sleep_ms(1000)
try:
    print("Starting transceiver...")

    remoteControllerConnection()
    # asyncio.run(ReemoteControler.messageReceiver(gameManager.start, gameManager.reset))
    # asyncio.run(main(ReemoteControler, peer_mac))
except KeyboardInterrupt:
    print("Stopping transceiver...")
    RemoteControler.close()

