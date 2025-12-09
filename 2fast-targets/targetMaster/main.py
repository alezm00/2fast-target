import machine
import utime
from oled import OLED_Display, Logger
import asyncio


display = OLED_Display(scl_pin=22, sda_pin=21)
log = Logger(display)

log.log(["System Initialized", "Awaiting Commands..."])

class Game:
    def __init__(self):
        pass


    def start(self):
        log.log(["Game Started"])






