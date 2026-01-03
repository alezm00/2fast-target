from machine import Pin
import asyncio
import utime
from random import randrange



from config import *



class GameManager:
    def def __init__(self, keypad, led_manager, remote_controller):
        self.sequence = None
        self.keypad = keypad
        self.Led_Manager = led_manager
        self.Remote_Controller = remote_controller
        self.startTime = utime.time_ns()
        self.gameActive = False
        self.buttonTimeout = TARGET_TIMEOUT_MS

    def shuffle(self, array):
        for i in range(len(array)-1, 0, -1):
            j = randrange(i+1)
            array[i], array[j] = array[j], array[i]

    def randomizer(self):
        target_sequence = [str(i) for i in range(0,25)]
        self.shuffle(target_sequence)
        return target_sequence

    async def start(self):
        self.gameActive = True
        self.sequence = self.randomizer()
        print("Game Started! Sequence:", self.sequence)

        self.Led_Manager.trafficLight()


        self.Led_Manager.clear()


        self.startTime = utime.time_ns()
        await self.gameLoop()

    async def stop(self):
        if not self.gameActive:
            return
        end_time = utime.time_ns()
        self.Led_Manager.allToggleBlink(4,100)


        self.gameActive = False

        elapsed_time = (end_time - self.startTime) / 1_000_000
        print("Game Over! Time:", elapsed_time, "ms")
        await self.Remote_Controller.sendMessage(f"ENDGAME:{elapsed_time:.2f}")


    async def gameLoop(self):
        buttonTimeoutStart = utime.ticks_ms()
        while self.gameActive and len(self.sequence) > 0:  # Check sequence length
            print("Waiting for key:", self.sequence[0])

            if utime.ticks_diff(utime.ticks_ms(), buttonTimeoutStart) > self.buttonTimeout:
                print("Timeout! No key pressed in time.")
                self.Led_Manager.ledOFF(self.sequence[0])
                self.sequence.pop(0)
                buttonTimeoutStart = utime.ticks_ms()

                if len(self.sequence) == 0:
                    await self.stop()
                    break

                await asyncio.sleep_ms(100)
                continue

            key_pressed = self.keypad.read_keypad()
            self.Led_Manager.ledON(self.sequence[0])

            if key_pressed is not None and key_pressed == self.sequence[0]:
                print("Correct key pressed:", key_pressed)

                self.Led_Manager.ledOFF(self.sequence[0])
                self.sequence.pop(0)
                buttonTimeoutStart = utime.ticks_ms()

                if len(self.sequence) == 0:
                    await self.stop()
                    break

                await asyncio.sleep_ms(100)

            await asyncio.sleep_ms(10)  # Changed from 1000 to 10ms for responsiveness

    async def reset(self):
        if not self.gameActive:
            return

        endTime = utime.time_ns()
        elapsedTime = (endTime - self.startTime) / 1_000_000_000
        print("Game RESET! Time:", elapsedTime, "ms")

        self.gameActive = False
