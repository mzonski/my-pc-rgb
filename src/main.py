import atexit
import logging
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Callable

from aura_device import AsusAuraLedDevice
from corsair_lighting_node import CorsairLightingNodeController
from ene_sync_controller import ENESyncController
from led_controller_interface import LEDController
from utils import RGBColor, DEFAULT_COLOR

logger = logging.getLogger(__name__)

from device_config import (
    RAM_BUS_NUMBER,
    RAM_DEVICE_NAME,
    RAM1_BUS_ADDRESS,
    RAM2_BUS_ADDRESS,
    GPU_BUS_NUMBER,
    GPU_BUS_ADDRESS,
    GPU_DEVICE_NAME,
)


class SyncedRGBController(LEDController):
    def __init__(self):
        self.controllers: List[LEDController] = [
            ENESyncController(
                [
                    (RAM_BUS_NUMBER, RAM1_BUS_ADDRESS, RAM_DEVICE_NAME),
                    (RAM_BUS_NUMBER, RAM2_BUS_ADDRESS, RAM_DEVICE_NAME),
                    (GPU_BUS_NUMBER, GPU_BUS_ADDRESS, GPU_DEVICE_NAME),
                ]
            ),
            CorsairLightingNodeController(),
            AsusAuraLedDevice(),
        ]
        self.running = False
        logger.info("Synced RGB Controller initialized")

    def _execute(self, func: Callable, *args, **kwargs) -> None:
        with ThreadPoolExecutor() as executor:
            list(executor.map(lambda device: func(device, *args, **kwargs), self.controllers))

    def set_static_color(self, color: RGBColor) -> None:
        self._execute(lambda d, c: d.set_static_color(c), color)

    def set_color(self, colors: RGBColor | List[RGBColor]) -> None:
        self._execute(lambda d, c: d.set_color(c), colors)

    def turn_on(self) -> None:
        self._execute(lambda d: d.turn_on())

    def turn_off(self) -> None:
        self._execute(lambda d: d.turn_off())

    def run(self) -> None:
        self.running = True
        try:
            self.turn_on()
            logger.info("RGB Controller service running")
            time.sleep(1)

            self.set_static_color(DEFAULT_COLOR)

            signal.pause()

        except Exception as e:
            logger.error("Error in main loop: %s", e)
            raise

    def stop(self) -> None:
        logger.info("Stopping RGB Controller service")
        self.running = False
        self.turn_off()


def main():
    closed = False

    controller = SyncedRGBController()

    def signal_handler(signum=None, _frame=None):
        logger.info("Received signal %s, shutting down...", signum)
        _cleanup()
        sys.exit(0)

    def _cleanup():
        nonlocal closed, controller

        if not closed:
            closed = True
            controller.stop()

    atexit.register(_cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        controller.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error("Fatal error: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s - %(message)s")
    # logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    main()
