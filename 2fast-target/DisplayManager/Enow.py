import network
import aioespnow # type: ignore
import asyncio


from config import *




class EspNowReemoteControler:
    def __init__(self,peerMac=peer_mac):
        # Initialize Wi-Fi in station mode
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        self.sta.config(channel=1)  # Set channel explicitly if packets are not received
        self.sta.disconnect()

        self.peerMac = peerMac

        # Initialize AIOESPNow
        self.E = aioespnow.AIOESPNow()
        try:
            status = self.E.active(True)
            print("AIOESPNow status:", status)
        except OSError as err:
            print("Failed to initialize AIOESPNow:", err)
            raise

        try:
            peer = self.E.add_peer(peerMac)
            print("Added peer:", peer, peerMac.hex(), peerMac)
        except OSError as err:
            print("Failed to add peer:", err)
            raise

    async def sendMessage(self, message, retry=5, callback=None):
        print(f"Sending message: {message} to {self.peerMac.hex(),self.peerMac, retry} attempts")
        for _ in range(retry):
            try:
                a = await self.E.asend(self.peerMac, message, sync=True)
                if a:
                    print(f"Sent message: {message}", a)
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
        while True:
            try:
                async for mac, msg in self.E:
                    print(f"Received from {mac.hex()}: {msg.decode()}")
                    if callback:
                        exit = callback(msg.decode(), mac or None)
            except OSError as err:
                print("Receive error:", err)
                await asyncio.sleep(5)
            if exit:
                print("Exiting message receiver loop.", msg.decode())
                return

    def close(self):
        self.E.active(False)
        self.sta.active(False)
