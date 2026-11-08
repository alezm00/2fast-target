"""Hardware constants (pins, matrix geometry). Tunable parameters live in
settings.py and are editable at runtime from the web interface."""

VERSION = "2.0.0"

# --- Target matrix: 5x5, index = row * COLS + col -------------------------
ROWS = 5
COLS = 5
N = ROWS * COLS

# Keypad (pressure switches). Columns are driven, rows are read (pull-up).
KEY_COL_PINS = (14, 13, 12, 11, 10)
KEY_ROW_PINS = (18, 8, 3, 46, 9)

# LED matrix. A LED is lit when its row line AND its column line are low.
LED_COL_PINS = (1, 2, 42, 41, 40)
LED_ROW_PINS = (39, 38, 37, 36, 35)
LED_ACTIVE_LOW = True

# On-board RGB status LED (None to disable)
STATUS_PIN = 48

# Physical START button wired to the master (active low, internal pull-up
# to GND). Starts the game selected in the web interface. None disables it.
BTN_START_PIN = 4

# Hardware watchdog: reboots the board if the main loop hangs
ENABLE_WDT = True
WDT_TIMEOUT_MS = 20000

HTTP_PORT = 80
