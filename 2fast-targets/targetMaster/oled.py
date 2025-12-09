# Complete project details at https://RandomNerdTutorials.com/micropython-programming-with-esp32-and-esp8266/

from machine import Pin, SoftI2C
import ssd1306
from time import sleep
import asyncio

class OLED_Display:
    def __init__(self, scl_pin, sda_pin, width = 128, height = 64):
        self.i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin))
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c)

    def display_text(self, lines):
        self.oled.fill(0)  # Clear the display
        for i, line in enumerate(lines):
            self.oled.text(line, 0, i * 10)  # Adjust y position for each line
        self.oled.show()




class Logger:
    def __init__(self, display):
        self.display = display

    async def _log(self, message):
        self.display.display_text(message)

    def log(self, message):
        asyncio.run(self._log(message))
