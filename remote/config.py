"""Radio remote: a tiny ESP32 with one or two buttons.

It sends ESP-NOW broadcast frames to the master, no pairing of MAC addresses
needed; only the code (SECRET) and the radio channel must match the master.
"""
CHANNEL = 1            # must equal "Canale WiFi" in the master settings
SECRET = "2fast"       # must equal "Codice di abbinamento telecomando"

START_PIN = 15         # press: start/stop toggle (None = unused)
STOP_PIN = 14          # press: stop            (None = unused)
LED_PIN = 2            # feedback LED          (None = unused)

START_MODE = None      # e.g. "reflex" to always start that mode; None = last used
REPEATS = 3            # every command is sent this many times (no ACK on broadcast)
LOCKOUT_MS = 600       # ignore further presses for this long
