from abc import ABC, abstractmethod

from utils import RGBColor


class LEDController(ABC):
    @abstractmethod
    def set_static_color(self, color: RGBColor) -> None:
        pass

    @abstractmethod
    def turn_on(self) -> None:
        pass

    @abstractmethod
    def turn_off(self) -> None:
        pass
