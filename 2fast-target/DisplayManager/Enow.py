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

    async def sendMessage(self, message, retry=5, callback=None):
        for _ in range(retry):
            try:
                a = await self.E.asend(self.peerMac, message, sync=True)
                if a:
                    print(f"Sent message: {message}", a)
                    #await NeoLogger.blink(2, "green")  # Changed from asyncio.run()
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
                async for mac, msg in self.E:
                    try:
                        text = msg.decode()
                    except UnicodeError:
                        print("Ignoring undecodable message from", mac.hex())
                        continue
                    print("Received from", mac.hex(), ":", text)
                    if callback:
                        try:
                            should_exit = await callback(text, mac)
                        except Exception as err:  # a bad handler must not kill the receiver
                            print("Message handler error:", repr(err))
                            continue
                        if should_exit:
                            print("Exiting message receiver loop.", text)
                            return "Exit received"
            except OSError as err:
                print("Receive error:", err)
                await asyncio.sleep(1)


    def close(self):
        self.E.active(False)
        self.sta.active(False)
