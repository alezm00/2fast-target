import network
import aioespnow # type: ignore
import asyncio
import time



from log import NeoLogger
from config import START_MESSAGE, STOP_MESSAGE, peer_mac


# Initialize Wi-Fi in station mode
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1)  # Set channel explicitly if packets are not received
sta.disconnect()

NeoLogger = NeoLogger()





class EspNowReemoteControler:
    def __init__(self,peer_mac=peer_mac):
        # Initialize AIOESPNow
        self.E = aioespnow.AIOESPNow()
        try:
            self.E.active(True)
        except OSError as err:
            NeoLogger.purple()
            print("Failed to initialize AIOESPNow:", err)
            raise

        try:
            self.E.add_peer(peer_mac)
        except OSError as err:
            NeoLogger.blue()
            print("Failed to add peer:", err)
            raise

    async def sendMessage(self, message, retry=5):
        for _ in range(retry):
            try:
                if await self.E.asend(peer_mac, message, sync=True):
                    print(f"Sent message: {message}")
                    asyncio.run(NeoLogger._blink(2, "green"))
                    return True
                else:
                    print("Failed to send message")
            except OSError as err:
                print("Send error:", err)
            await asyncio.sleep(.5)
        return False


    async def messageReceiver(self,started_callback=None, stopped_callback=None):
        while True:
            try:
                async for mac, msg in self.E:
                    print(f"Received from {mac.hex()}: {msg.decode()}")
                    if msg.decode() == START_MESSAGE and started_callback:
                        started_callback()
                    elif msg.decode() == STOP_MESSAGE and stopped_callback:
                        stopped_callback()
            except OSError as err:
                print("Receive error:", err)
                await asyncio.sleep(5)

    def close(self):
        self.E.active(False)
        sta.active(False)
