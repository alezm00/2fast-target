from machine import Pin


# Define the LCD I2C address and dimensions
buttonPin = Pin(15, Pin.IN, Pin.PULL_UP)  # Button connected to GPIO15
key_pin = Pin(12, Pin.IN, Pin.PULL_UP)  # Key to
resetPin = Pin(14, Pin.IN, Pin.PULL_UP)


I2C_ADDR = 0x27
I2C_NUM_ROWS = 4
I2C_NUM_COLS = 20
I2C_SDA_PIN = Pin(21)
I2C_SCL_PIN = Pin(22)



peer_mac = b'\x3c\xdc\x75\x6b\xc6\x30'  # Example peer MAC for unicast

INIT_MESSAGE = "INIT"
START_MESSAGE = "START"
STOP_MESSAGE = "RESET"
MODE_MESSAGE = "DEMO"

BUTTON_DEBOUNCE_MS = 300
RESET_DEBOUNCE_MS = 300
