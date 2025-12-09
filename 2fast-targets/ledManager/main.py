# from machine import Pin
# from utime import sleep

# pins = [Pin(i, Pin.OUT) for i in (18,19,21,27,26,25,33,32)]
# pins2 = [Pin(i, Pin.OUT) for i in (15,2,4,16,17,5,22,23)]
# print(pins)

# while True:
#     for i in pins:
#         print(i)
#         i.value(1)
#         sleep(0.1)
#         i.value(0)
#         sleep(0.1)
#     for j in pins2:
#         print(j)
#         j.value(1)
#         sleep(0.1)
#         j.value(0)
#         sleep(0.1)


# Bidirectional UART Code (Runs on both ESP32 boards)

from machine import UART, Pin
import time


led = Pin(2, Pin.OUT)

# --- CONFIGURATION ---
# IMPORTANT: Change this on each ESP32 to distinguish them
DEVICE_NAME = "Node B"  # Change to "Node B" on the second ESP32
BAUDRATE = 115200

# Use UART 2 (ID=2)
TX_PIN = 35
RX_PIN = 34
# ---------------------

# Initialize the UART peripheral
uart = UART(2, baudrate=BAUDRATE)

send_counter = 0

def send_message(msg):
    """Sends a message over UART, adding a newline for separation."""
    # Encode string to bytes and add a newline character (b'\n')
    uart.write(msg)
    print(f"[{DEVICE_NAME}] SENT: {msg}")

def check_for_incoming():
    """Checks for and reads any available complete line from UART."""
    # Check if any data is available
    if uart.any():
        # Read until the newline character
        incoming_message = uart.readline()

        if incoming_message:
            # Decode the bytes to a string and strip whitespace
            decoded_message = incoming_message
            print(f"[{DEVICE_NAME}] RECEIVED: {decoded_message}")
            led.toggle()  # Toggle LED to indicate message received

# --- Main Loop ---
print(f"--- {DEVICE_NAME} Ready (TX:{TX_PIN}, RX:{RX_PIN}) ---")

while True:
    # 1. SENDING PHASE
    # Craft a simple status message including the counter
    status_msg = f"{DEVICE_NAME} is alive. Counter: {send_counter}"
    send_message(status_msg)
    send_counter += 1

    # 2. RECEIVING PHASE
    # Immediately check if the other device has sent a message
    # This prevents the program from getting "stuck" just waiting to send
    check_for_incoming()

    # Wait for a short period before the next cycle
    time.sleep(1)
