from machine import Pin
import asyncio
import utime
from random import randrange



from config import *
from keypad import KeyPad
from led import LedManager
from log import NeoLogger



class GameManager:
    def __init__(self,keypad, LedManager):
        self.keypad = keypad
        self.LedManager = LedManager
        self.startTime = utime.time_ns()
        self.gameActive = False
        self.buttonTimeout = TARGET_TIMEOUT_MS

    def shuffle(self, array):
        for i in range(len(array)-1, 0, -1):
            j = randrange(i+1)
            array[i], array[j] = array[j], array[i]

    def randomizer(self):
        x = [str(i) for i in range(0,25)]
        self.shuffle(x)
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
        elapsedTime = (endTime - self.startTime) / 1_000_000_000
        print("Game Over! Time:", elapsedTime, "ms")

        self.gameActive = False


    def gameLoop(self):
        buttonTimeoutStart = utime.ticks_ms()
        while self.gameActive:
            print("Waiting for key:", self.sequence[0])

            if utime.ticks_diff(utime.ticks_ms(), buttonTimeoutStart) > self.buttonTimeout:
                if len(self.sequence) == 0:
                    self.stop()
                print("Timeout! No key pressed in time.")
                self.LedManager.ledOFF(self.sequence[0])
                self.sequence.pop(0)
                buttonTimeoutStart = utime.ticks_ms()
                utime.sleep_ms(100)

            key_pressed = self.keypad.read_keypad()
            self.LedManager.ledON(self.sequence[0])

            if key_pressed is not None and key_pressed == self.sequence[0]:
                print("Correct key pressed:", key_pressed)

                self.LedManager.ledOFF(self.sequence[0])
                self.sequence.pop(0)
                buttonTimeoutStart = utime.ticks_ms()
                utime.sleep_ms(100)
            utime.sleep_ms(10)

            if len(self.sequence) == 0:
                self.stop()




    def reset(self):
        pass
