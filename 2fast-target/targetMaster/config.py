from machine import Pin



column_pins = [Pin(14),Pin(13),Pin(12),Pin(11),Pin(10)]
row_pins = [Pin(18),Pin(8),Pin(3),Pin(46),Pin(9)]
keys = [
    ['0', '1', '2', '3', '4'],
    ['5', '6', '7', '8', '9'],
    ['10', '11', '12', '13', '14'],
    ['15', '16', '17', '18', '19'],
    ['20', '21', '22', '23', '24']
]
LED_column_pins = [Pin(1),Pin(2),Pin(42),Pin(41),Pin(40)]
LED_row_pins = [Pin(39),Pin(38),Pin(37),Pin(36),Pin(35)]



TARGET_TIMEOUT_MS = 100000000000  # milliseconds




peer_mac = b'\x58\xbf\x25\xaa\xd7\xec'  # Example peer MAC for unicast

INIT_MESSAGE = "INIT"
START_MESSAGE = "START"
STOP_MESSAGE = "RESET"
