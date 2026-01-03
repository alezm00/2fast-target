import network
import aioespnow # type: ignore
import asyncio
import time



from log import NeoLogger
from config import *


# Initialize Wi-Fi in station mode
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1)  # Set channel explicitly if packets are not received
sta.disconnect()

NeoLogger = NeoLogger()





class EspNowRemoteControler:
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

    async def sendMessage(self, message, retry=5, callback=None):
        for _ in range(retry):
            try:
                a = await self.E.asend(peer_mac, message, sync=True)
                if a:
                    print(f"Sent message: {message}", a)
                    await NeoLogger.blink(2, "green")  # Changed from asyncio.run()
                    if callback:
                        callback()
                    return True
                else:
                    print("Failed to send message", a)
            except OSError as err:
                print("Send error:", err)
            await asyncio.sleep(.5)
        return False


    async def messageReceiver(self, callback=None):
        print("Starting message receiver...")
        while True:
            try:
                print("message receiver...")
                async for mac, msg in self.E:
                    print(f"Received from {mac.hex()}: {msg.decode()}")
                    if callback:
                        should_exit = await callback(msg, mac)  # Changed to awaito await
                        if should_exit:
                            print("Exiting message receiver loop.", msg.decode())
                            return "Exit received"
            except OSError as err:
                print("Receive error:", err)
                await asyncio.sleep(5)


    def close(self):
        self.E.active(False)
        sta.active(False)
