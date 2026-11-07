import asyncio
import utime
from random import randrange

from config import *


class GameManager:
    def __init__(self, keypad, led_manager, remote_controller):
        self.sequence = []
        self.keypad = keypad
        self.Led_Manager = led_manager
        self.Remote_Controller = remote_controller
        self.startTime = utime.ticks_ms()
        self.gameActive = False
        self.buttonTimeout = TARGET_TIMEOUT_MS
        self.demoButtonTimeout = DEMO_TARGET_TIMEOUT_MS
        self.buttonTimeoutStart = 0

    def shuffleSequence(self, array):
        for i in range(len(array) - 1, 0, -1):
            j = randrange(i + 1)
            array[i], array[j] = array[j], array[i]

    def randomizer(self):
        target_sequence = [str(i) for i in range(25)]
        self.shuffleSequence(target_sequence)
        return target_sequence

    def elapsedMs(self):
        return utime.ticks_diff(utime.ticks_ms(), self.startTime)

    async def start(self):
        self.gameActive = True
        self.sequence = self.randomizer()
        print("Game Started! Sequence:", self.sequence)

        await self.Led_Manager.trafficLight()
        self.Led_Manager.clear()

        self.startTime = utime.ticks_ms()
        await self.gameLoop()

    async def startDemo(self):
        self.gameActive = True
        self.startTime = utime.ticks_ms()
        await self.Led_Manager.trafficLight()
        self.Led_Manager.clear()
        await self.demoMode()

    async def _step(self, timeout):
        """Handle one polling tick for the current target.

        Returns False when there is no target left."""
        if not self.sequence:
            return False

        target = self.sequence[0]
        self.Led_Manager.ledON(target)
        key_pressed = self.keypad.read_keypad()

        if key_pressed is not None and key_pressed == target:
            print("Correct key pressed:", key_pressed)
        elif utime.ticks_diff(utime.ticks_ms(), self.buttonTimeoutStart) > timeout:
            print("Timeout, current:", target)
        else:
            return True

        # target hit or missed: move on to the next one
        self.Led_Manager.ledOFF(target)
        self.sequence.pop(0)
        self.buttonTimeoutStart = utime.ticks_ms()
        await asyncio.sleep_ms(50)
        return True

    async def gameLoop(self):
        self.buttonTimeoutStart = utime.ticks_ms()

        while self.gameActive and self.sequence:
            await self._step(self.buttonTimeout)
            await asyncio.sleep_ms(10)

        await self.stop()

    async def demoMode(self):
        print("Starting demo mode")
        self.sequence = self.randomizer()
        self.buttonTimeoutStart = utime.ticks_ms()

        while self.gameActive:
            if len(self.sequence) < 2:
                self.sequence = self.randomizer()
                print("New demo run", self.sequence)
                await asyncio.sleep_ms(1000)
                self.buttonTimeoutStart = utime.ticks_ms()

            await self._step(self.demoButtonTimeout)
            await asyncio.sleep_ms(10)

        await self.stop()

    async def stop(self):
        if not self.gameActive:
            return
        elapsed_time = self.elapsedMs()
        self.gameActive = False
        self.buttonTimeoutStart = 0
        self.sequence = []
        self.Led_Manager.allToggleBlink(4, 100)
        self.Led_Manager.clear()
        print("Game Over! Time:", elapsed_time, "ms")
        await self.Remote_Controller.sendMessage("ENDGAME:{:.2f}".format(elapsed_time))

    async def reset(self):
        self.Led_Manager.clear()
        if not self.gameActive:
            return
        elapsed_time = self.elapsedMs()
        print("Game RESET! Time:", elapsed_time, "ms")
        self.gameActive = False
        self.sequence = []
        await self.Remote_Controller.sendMessage("ENDGAME_RESET:{:.2f}".format(elapsed_time))
