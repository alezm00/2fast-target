from machine import Pin
import asyncio
import utime
from random import randrange




from config import *
from keypad import KeyPad
from led import LedManager
#### CONFIG



# for i in LED_column_pins:
#     i.init(Pin.OUT)
# for i in LED_row_pins:
#     i.init(Pin.OUT)

print("diocan", utime.time_ns())


####


print("cols:", str([i.value() for i in column_pins]))
print("rows:", str([i.value() for i in row_pins]))
KeyPad = KeyPad(row_pins, column_pins, keys)


LedManager = LedManager(LED_row_pins, LED_column_pins, keys)




def shuffle(array):
    "Fisher–Yates shuffle"
    for i in range(len(array)-1, 0, -1):
        j = randrange(i+1)
        array[i], array[j] = array[j], array[i]

class GameManager:
    def __init__(self,keypad, LedManager):
        self.keypad = keypad
        self.LedManager = LedManager
        self.startTime = utime.time_ns()
        self.gameActive = False



    def randomizer(self):
        x = [str(i) for i in range(0,5)]
        shuffle(x) # type: ignore
        return x

    def start(self):
        self.gameActive = True
        self.sequence = self.randomizer()
        print("Game Started! Sequence:", self.sequence)

        self.LedManager.trafficLight()


        self.LedManager.clear()


        self.startTime = utime.time_ns()
        self.gameLoop()





    def stop(self):
        if not self.gameActive:
            return

        endTime = utime.time_ns()
        elapsedTime = (endTime - self.startTime) / 1_000_000
        print("Game Over! Time:", elapsedTime, "ms")

        self.gameActive = False


    def gameLoop(self):
        while self.gameActive:
            print("Waiting for key:", self.sequence[0])
            key_pressed = self.keypad.read_keypad()

            self.LedManager.ledON(self.sequence[0])

            if key_pressed is not None and key_pressed == self.sequence[0]:
                print("Correct key pressed:", key_pressed)

                self.sequence.pop(0)
                # print("KEY", key_pressed)
                # await self.LedManager.display_led(key_pressed)
                self.LedManager.ledOFF(key_pressed)
                utime.sleep_ms(100)
            utime.sleep_ms(10)

            if len(self.sequence) == 0:
                self.stop()




    def reset(self):
        pass



gameManager = GameManager(KeyPad, LedManager)


gameManager.start()


















# while True:
#     key_pressed = KeyPad.read_keypad()
#     if key_pressed:
#         # print("cols:", str([i.value() for i in column_pins]))
#         # print("rows:", str([i.value() for i in row_pins]))

#         print("KEY",key_pressed)
#         # LedManager.display_led(key_pressed)
#         asyncio.run(LedManager.display_led(key_pressed))

#     utime.sleep_ms(100)






