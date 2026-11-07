import machine
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

utime.sleep_ms(1000)

def waitingText():
    lcd.clear()
    lcd.putstr("2Fast Target\n\nWaiting for\nbutton press...")
    print("Waiting for button press...",utime.ticks_ms())

waitingText()
gamestatus = "WAITING"

# Button IRQs only record the request: sending (asyncio, radio) must never
# run inside an interrupt handler. A background task does the actual send.
pending_action = None
buttonlastPress = utime.ticks_ms() - BUTTON_DEBOUNCE_MS
resetlastPress = utime.ticks_ms() - RESET_DEBOUNCE_MS


def button_handler(pin):
    global buttonlastPress, pending_action
    now = utime.ticks_ms()
    if utime.ticks_diff(now, buttonlastPress) < BUTTON_DEBOUNCE_MS:
        return
    buttonlastPress = now
    # key held while pressing the button -> demo mode
    pending_action = MODE_MESSAGE if not key_pin.value() else START_MESSAGE


def reset_button(pin):
    global resetlastPress, pending_action
    now = utime.ticks_ms()
    if utime.ticks_diff(now, resetlastPress) < RESET_DEBOUNCE_MS:
        return
    resetlastPress = now
    pending_action = STOP_MESSAGE  # reset always wins


async def buttonWorker():
    global pending_action
    while True:
        action = pending_action
        if action is not None:
            pending_action = None
            print("Button action:", action)
            ok = await RemoteControler.sendMessage(action)
            if not ok:
                print("Master did not acknowledge", action)
        await asyncio.sleep_ms(20)


def timeString(time_ms: float = 0.0) -> str:
    # Convert to integer milliseconds
    time_ms = int(time_ms)
    # Convert milliseconds to MM:SS:MS format
    minutes = time_ms // 60000
    seconds = (time_ms % 60000) // 1000
    milliseconds = time_ms % 1000

    return f"{minutes:02d}:{seconds:02d}:{milliseconds:03d}"


async def message_callback(msg:str, mac):
    global gamestatus
    print("Message callback triggered with msg:", msg, "gamestatus:", gamestatus)
    if msg == START_MESSAGE:
        gamestatus = msg
        print("START message received, starting game.")
        lcd.clear()
        lcd.putstr("START!\nGame started...")
        #led_blink(led_pin, times=5, delay_ms=25)

    elif msg == MODE_MESSAGE:
        gamestatus = "DEMO"
        print("DEMO message received.")
        lcd.clear()
        lcd.putstr("DEMO!\nDemo game started.")
        #led_blink(led_pin, times=20, delay_ms=50)

    elif msg == STOP_MESSAGE:
        gamestatus = "WAITING"
        print("STOP message received, stopping game.")
        lcd.clear()
        lcd.putstr("STOP!\nGame stopped...")
        #led_blink(led_pin, times=10, delay_ms=100)
        await asyncio.sleep(3)
        waitingText()

    elif "ENDGAME" in msg:
        gamestatus = "WAITING"
        print("ENDGAME message received.", msg)

        try:
            time_ms = float(msg.split(":")[1].strip())
        except (IndexError, ValueError):
            print("Malformed ENDGAME message:", msg)
            return
        time_str = timeString(time_ms)

        lcd.clear()
        lcd.putstr(f"GAME END!\nTime: {time_str}")
        led_blink(led_pin, times=15, delay_ms=50)


async def main():
    asyncio.create_task(buttonWorker())
    await RemoteControler.messageReceiver(callback=message_callback)


try:
    buttonPin.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)
    resetPin.irq(trigger=Pin.IRQ_FALLING, handler=reset_button)
    asyncio.run(main())
except KeyboardInterrupt:
    print("Keyboard interrupt")
    lcd.backlight_off()
    lcd.display_off()
    RemoteControler.close()
except Exception as err:
    # Unrecoverable error: reboot instead of hanging with a frozen screen
    print("Fatal error:", repr(err))
    try:
        lcd.clear()
        lcd.putstr("Errore, riavvio...")
    except Exception:
        pass
    utime.sleep_ms(2000)
    machine.reset()
