from machine import Pin, SoftI2C
from machine_i2c_lcd import I2cLcd
import utime
import asyncio


from Enow import EspNowRemoteController
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

RemoteControler = EspNowRemoteController(peer_mac)



print("LCD test",utime.ticks_ms())
lcd.putstr("2Fast Target\n\nWaiting for master\nconnection...")

utime.sleep_ms(2000)

connection_established = False

def on_connection_established():
    global connection_established
    connection_established = True

    print("Connection established callback triggered")

    lcd.clear()
    lcd.putstr("Master connected!\nReady to start.")
    led_blink(led_pin, times=10, delay_ms=50)
    return True


while not connection_established:
    asyncio.run(RemoteControler.sendMessage(INIT_MESSAGE,retry=1,callback=on_connection_established))
    utime.sleep_ms(1000)  # Wait before retrying
    pass

utime.sleep_ms(2000)

def waitingText():
    lcd.clear()
    lcd.putstr("2Fast Target\n\nWaiting for\nbutton press...")
    print("Waiting for button press...",utime.ticks_ms())

waitingText()
gamestatus = "WAITING"

debounceDelay = 5000  # milliseconds
buttonlastPress = utime.ticks_ms()-debounceDelay
def button_handler(pin):
    global buttonlastPress
    global gamestatus
    if utime.ticks_diff(utime.ticks_ms(), buttonlastPress) < debounceDelay:
        return
    buttonlastPress = utime.ticks_ms()
    print("Button pressed, sending START message")

    if gamestatus == STOP_MESSAGE or gamestatus == "WAITING":
        asyncio.run(RemoteControler.sendMessage(START_MESSAGE))
    if gamestatus == START_MESSAGE:
        asyncio.run(RemoteControler.sendMessage(STOP_MESSAGE))



def message_callback(msg, mac):
    global gamestatus
    print("Message callback triggered with msg:", msg)
    if msg == START_MESSAGE:
        gamestatus = msg
        print("START message received, starting game.")
        lcd.clear()
        lcd.putstr("START!\nStarting game...")
        led_blink(led_pin, times=5, delay_ms=25)
    elif msg == STOP_MESSAGE:
        gamestatus = msg
        print("STOP message received, stopping game.")
        lcd.clear()
        lcd.putstr("STOP!\nStopping game...")
        led_blink(led_pin, times=10, delay_ms=100)
        asyncio.sleep(3)
        waitingText()
    elif "ENDGAME" in msg:
        gamestatus = "WAITING"
        print("ENDGAME message received.")
        time_ms = float(msg.split(":")[1].strip())

        # Convert to integer milliseconds
        time_ms = int(time_ms)

        # Convert milliseconds to MM:SS:MS format
        minutes = time_ms // 60000
        seconds = (time_ms % 60000) // 1000
        milliseconds = time_ms % 1000

        time_str = f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"

        lcd.clear()
        lcd.putstr(f"GAME END!\nTime: {time_str}")
        led_blink(led_pin, times=15, delay_ms=50)


try:
    buttonPin.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)

    asyncio.run(RemoteControler.messageReceiver(callback=message_callback))


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
