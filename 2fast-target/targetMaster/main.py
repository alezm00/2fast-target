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

ReemoteControler = EspNowReemoteControler()


print("cols:", str([i.value() for i in column_pins]))
print("rows:", str([i.value() for i in row_pins]))
KeyPad = KeyPad(row_pins, column_pins, keys)
LedManager = LedManager(LED_row_pins, LED_column_pins, keys)





gameManager = GameManager(KeyPad, LedManager)




# gameManager.start()





# Main async function
# async def main(e, peer):
#     # Run send, receive, and stats tasks concurrently
#     await asyncio.gather(send_messages(e, peer), receive_messages(e), print_stats(e))

try:
    print("Starting transceiver...")
    asyncio.run(ReemoteControler.messageReceiver(gameManager.start, gameManager.stop))
    # asyncio.run(main(ReemoteControler, peer_mac))
except KeyboardInterrupt:
    print("Stopping transceiver...")
    ReemoteControler.close()

