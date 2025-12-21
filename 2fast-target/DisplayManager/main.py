
from machine import Pin, SoftI2C
from machine_i2c_lcd import I2cLcd
import utime
import asyncio


from Enow import EspNowReemoteControler
from config import *



led_pin = Pin(2, Pin.OUT)

def led_blink(pin, times=5, delay_ms=20):
    for _ in range(times):
        pin.on()
        utime.sleep_ms(delay_ms)
        pin.off()
        utime.sleep_ms(delay_ms)






# Initialize I2C and LCD objects
i2c = SoftI2C(sda=I2C_SDA_PIN, scl=I2C_SCL_PIN, freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

RemoteControler = EspNowReemoteControler(peer_mac)





print("LCD test",utime.ticks_ms())
lcd.putstr("2Fast Target\n\nWaiting for master\nconnection...")
utime.sleep_ms(2000)

connection_established = False
def on_connection_established(msg):
    if msg == INIT_MESSAGE:
        global connection_established
        connection_established = True
        print("Connection established callback triggered")
        lcd.clear()
        lcd.putstr("Master connected!\nReady to start.")
        led_blink(led_pin, times=10, delay_ms=50)


while not connection_established:
    asyncio.gather(RemoteControler.sendMessage(INIT_MESSAGE),RemoteControler.messageReceiver(callback=on_connection_established))
    utime.sleep_ms(1000)  # Wait before retrying
    pass


lcd.clear()
lcd.putstr("2Fast Target\n\nWaiting for\nbutton press...")
print("Waiting for button press...",utime.ticks_ms())
debounceDelay = 5000  # milliseconds
buttonlastPress = utime.ticks_ms()-debounceDelay
def button_handler(pin):
    global buttonlastPress
    if utime.ticks_diff(utime.ticks_ms(), buttonlastPress) < debounceDelay:
        return
    buttonlastPress = utime.ticks_ms()
    print("Button pressed, sending START message")
    lcd.putstr("Button pressed!\nSending START")
    asyncio.run(RemoteControler.sendMessage(START_MESSAGE))





try:
    buttonPin.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)
except KeyboardInterrupt:
    print("Keyboard interrupt")
    lcd.backlight_off()
    lcd.display_off()
    RemoteControler.close()

# asyncio.run(RemoteControler.sendMessage(START_MESSAGE))



# try:
#     while True:
#         # Clear the LCD
#         # lcd.clear()
#         # Display two different messages on different lines
#         # By default, it will start at (0,0) if the display is empty
#         lcd.putstr("Hello World!")
#         sleep(2)
#         # lcd.clear()
#         # Starting at the second line (0, 1)
#         lcd.move_to(0, 1)
#         lcd.putstr("Hello World!")
#         sleep(2)

# except KeyboardInterrupt:
#     # Turn off the display
#     print("Keyboard interrupt")
#     lcd.backlight_off()
#     lcd.display_off()
