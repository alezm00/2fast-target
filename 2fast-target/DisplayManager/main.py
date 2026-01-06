from machine import Pin, SoftI2C
from machine_i2c_lcd import I2cLcd
import utime
import asyncio


from Enow import EspNowRemoteController
from config import *



led_pin = Pin(2, Pin.OUT)
key_pin = Pin(12, Pin.IN, Pin.PULL_UP)  # Key to



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

utime.sleep_ms(1000)

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
    print("Button pressed, sendingmessage")

    if gamestatus == STOP_MESSAGE or gamestatus == "WAITING":
        if not key_pin.value():
            print("Button pressed, key 1 ,sending DEMO message")
            asyncio.run(RemoteControler.sendMessage(MODE_MESSAGE))
        else:
            print("Button pressed, sending START message")
            asyncio.run(RemoteControler.sendMessage(START_MESSAGE))
    if gamestatus == START_MESSAGE or gamestatus == MODE_MESSAGE:
        asyncio.run(RemoteControler.sendMessage(STOP_MESSAGE))


def timeString(time_ms: float = 0.0) -> str:
    # Convert to integer milliseconds
    time_ms = int(time_ms)
    # Convert milliseconds to MM:SS:MS format
    minutes = time_ms // 60000
    seconds = (time_ms % 60000) // 1000
    milliseconds = time_ms % 1000

    return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"


def message_callback(msg, mac):
    global gamestatus
    print("Message callback triggered with msg:", msg)
    if msg == START_MESSAGE:
        gamestatus = msg
        print("START message received, starting game.")
        lcd.clear()
        lcd.putstr("START!\nGame started...")
        led_blink(led_pin, times=5, delay_ms=25)

    elif msg == MODE_MESSAGE:
        gamestatus = "DEMO"
        print("DEMO message received.")
        lcd.clear()
        lcd.putstr("DEMO!\nDemo game started.")
        led_blink(led_pin, times=20, delay_ms=50)

    elif msg == STOP_MESSAGE:
        gamestatus = msg
        print("STOP message received, stopping game.")
        lcd.clear()
        lcd.putstr("STOP!\nGame stopped...")
        led_blink(led_pin, times=10, delay_ms=100)
        asyncio.sleep(3)
        waitingText()

    elif "ENDGAME" in msg:
        gamestatus = "WAITING"
        print("ENDGAME message received.")

        time_ms = float(msg.split(":")[1].strip())
        time_str = timeString(time_ms)

        lcd.clear()
        lcd.putstr(f"GAME END!\nTime: {time_str}")
        led_blink(led_pin, times=15, delay_ms=50)

    elif "ENDGAME_RESET" in msg:
        gamestatus = "WAITING"
        print("ENDGAME_RESET message received.")

        time_ms = float(msg.split(":")[1].strip())
        time_str = timeString(time_ms)
        lcd.clear()
        lcd.putstr(f"GAME RESET!\nTime: {time_str}")
        led_blink(led_pin, times=15, delay_ms=50)

try:
    buttonPin.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)
    asyncio.run(RemoteControler.messageReceiver(callback=message_callback))
except KeyboardInterrupt:
    print("Keyboard interrupt")
    lcd.backlight_off()
    lcd.display_off()
    RemoteControler.close()
