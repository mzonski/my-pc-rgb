import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple, Callable

from ene_controller import ENEController
from led_controller_interface import LEDController
from utils import RGBColor

logger = logging.getLogger(__name__)


class ENESyncController(LEDController):
    def __init__(self, devices: Optional[List[Tuple[int, int, str]]] = None) -> None:
        self.devices: List[ENEController] = [
            ENEController(bus, addr, device_name) for bus, addr, device_name in devices
        ]
        logger.info("Sync Controller initialized with %d devices", len(self.devices))

    def _execute(self, func: Callable, *args, **kwargs) -> None:
        with ThreadPoolExecutor() as executor:
            list(executor.map(lambda device: func(device, *args, **kwargs), self.devices))

    def set_static_color(self, color: RGBColor) -> None:
        self._execute(lambda d, c: d.set_static_color(c), color)

    def set_color(self, colors: RGBColor | List[RGBColor]) -> None:
        self._execute(lambda d, c: d.set_color(c), colors)

    def turn_on(self) -> None:
        self._execute(lambda d: d.turn_on())

    def turn_off(self) -> None:
        self._execute(lambda d: d.turn_off())
