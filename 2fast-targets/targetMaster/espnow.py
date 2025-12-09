import network
import aioespnow # pyright: ignore[reportMissingImports]
import asyncio
import time

import config


# Initialize Wi-Fi in station mode
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.config(channel=1)  # Set channel explicitly if packets are not received
sta.disconnect()

# Initialize AIOESPNow
e = aioespnow.AIOESPNow()
try:
    e.active(True)
except OSError as err:
    print("Failed to initialize AIOESPNow:", err)
    raise



# Add peer for unicast reliability
try:
    e.add_peer(config.DISPLAYCONTROLLER)
    e.add_peer(config.LEDCONTROLLER)
except OSError as err:
    print("Failed to add peer:", err)
    raise


# Stats tracking
last_stats_time = time.time()
stats_interval = 10  # Print stats every 10 seconds
