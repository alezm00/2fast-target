import network
import aioespnow # type: ignore
import asyncio

from log import NeoLogger
from config import *


# Initialize Wi-Fi in station mode
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1)  # Set channel explicitly if packets are not received
sta.disconnect()

_logger = NeoLogger()


class EspNowRemoteControler:
    def __init__(self, peer_mac=peer_mac):
        self.peer_mac = peer_mac

        # Initialize AIOESPNow
        self.E = aioespnow.AIOESPNow()
        try:
            self.E.active(True)
        except OSError as err:
            _logger.purple()
            print("Failed to initialize AIOESPNow:", err)
            raise

        try:
            self.E.add_peer(self.peer_mac)
        except OSError as err:
            _logger.blue()
            print("Failed to add peer:", err)
            raise

    async def sendMessage(self, message, retry=5, callback=None):
        for _ in range(retry):
            try:
                ok = await self.E.asend(self.peer_mac, message, sync=True)
                if ok:
                    print("Sent message:", message, ok)
                    await _logger.blink(2, "green")
                    if callback:
                        callback()
                    return True
                print("Failed to send message", ok)
            except OSError as err:
                print("Send error:", err)
            await asyncio.sleep(.5)
        return False

    async def messageReceiver(self, callback=None):
        """Receive loop. The callback gets (msg: str, mac: bytes)."""
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
        sta.active(False)
