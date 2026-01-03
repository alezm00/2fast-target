import network
import aioespnow # type: ignore
import asyncio


from config import *




class EspNowRemoteController:
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


    async def messageReceiver(self, callback=None):
        while True:
            try:
                async for mac, msg in self.E:
                    print(f"Received from {mac.hex()}: {msg.decode()}")
                    if callback:
                        exit = callback(msg.decode(), mac or None)
                        # if exit:
                        #     print("Exiting message receiver loop.", msg.decode())
                        #     return
            except OSError as err:
                print("Receive error:", err)
                await asyncio.sleep(5)
    def close(self):
        self.E.active(False)
        self.sta.active(False)
