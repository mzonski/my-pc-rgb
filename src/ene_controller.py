import logging
from enum import IntEnum
from typing import List, Optional

from smbus3 import SMBus

from led_controller_interface import LEDController
from utils import DEFAULT_COLOR, DISABLED_COLOR, RGBColor

logger = logging.getLogger(__name__)


class Config(IntEnum):
    LED_COUNT = 0x03


class ApplyMode(IntEnum):
    APPLY = 0x01
    SAVE = 0xAA


class Registers(IntEnum):
    DEVICE_NAME = 0x1000
    CONFIG_TABLE = 0x1C00
    MODE = 0x8021
    APPLY = 0x80A0
    DIRECT = 0x8020
    COLORS_DIRECT_V2 = 0x8100
    COLORS_EFFECT_V2 = 0x8160


class LightMode(IntEnum):
    OFF = 0
    STATIC = 1


class ENEController(LEDController):
    def set_color(self, colors: RGBColor | List[RGBColor]) -> None:
        if isinstance(colors, tuple):
            r, g, b = colors
            colors_list = [colors] * self.led_count
            self._set_direct_mode(True, colors)
            logger.debug("Set direct color RGB(%d, %d, %d) for %d LEDs", r, g, b, self.led_count)
        else:
            colors_list = colors
            self._set_direct_mode(True, colors[0])
            logger.debug("Set %d individual colors", len(colors))

        self._write_colors(colors_list)

    def set_static_color(self, color: RGBColor) -> None:
        r, g, b = color
        colors_list = [color] * self.led_count
        self._set_direct_mode(False, color)
        logger.debug("Set static color RGB(%d, %d, %d) for %d LEDs", r, g, b, self.led_count)

        self._write_colors(colors_list)

    def turn_on(self) -> None:
        try:
            self._set_direct_mode(False, DEFAULT_COLOR)
            self._set_mode(LightMode.STATIC)
            self.set_color(DEFAULT_COLOR)
            self.apply()
            logger.debug("GPU LED turned on")
        except Exception as e:
            logger.error("Error turning on GPU LED: %s", e)
            raise

    def turn_off(self) -> None:
        try:
            self._set_direct_mode(False, DISABLED_COLOR)
            self._set_mode(LightMode.OFF)
            self.apply()
            logger.debug("GPU LED turned off")
        except Exception as e:
            logger.error("Error turning off GPU LED: %s", e)
            raise

    def __init__(self, bus_number: int, address: int, device_name: str) -> None:
        self.bus: SMBus = SMBus(bus_number)
        self.address: int = address
        self.device_name: str = self._get_device_name()

        if self.device_name != device_name:
            raise RuntimeError(
                f"Controller incorrectly initialized on bus {bus_number} at register {address}."
                + f"Expected device name {device_name}, got {self.device_name}"
            )

        self.config_table: List[int] = self._read_register_block(Registers.CONFIG_TABLE, 64)
        self.is_direct_mode = False
        self.light_mode = self._read_register(Registers.MODE)
        self.led_count: int = self.config_table[Config.LED_COUNT]

        logger.debug("ENE Controller initialized on bus %s at address 0x%02X", bus_number, address)
        logger.info("ENE Controller initialized with %d LEDs", self.led_count)

    def _read_register(self, register: int) -> int:
        try:
            reg_swapped = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
            self.bus.write_word_data(self.address, 0x00, reg_swapped)
            value = self.bus.read_byte_data(self.address, 0x81)
            logger.debug("Read 0x%02X from register 0x%04X", value, register)
            return value
        except Exception as e:
            logger.error("Error reading from register 0x%04X: %s", register, e)
            raise

    def _read_register_block(self, register: int, length: int) -> List[int]:
        try:
            data = [self._read_register(register + i) for i in range(length)]
            logger.debug("Read %d bytes from register 0x%04X", len(data), register)
            return data
        except Exception as e:
            logger.error("Error reading block from register 0x%04X: %s", register, e)
            raise

    def _write_register(self, register: int, value: int) -> None:
        try:
            reg_swapped = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
            self.bus.write_word_data(self.address, 0x00, reg_swapped)
            self.bus.write_byte_data(self.address, 0x01, value)
            logger.debug("Wrote 0x%02X to register 0x%04X", value, register)
        except Exception as e:
            logger.error("Error writing to register 0x%04X: %s", register, e)
            raise

    def _write_register_block(self, register: int, data: List[int]) -> None:
        try:
            reg_swapped = ((register << 8) & 0xFF00) | ((register >> 8) & 0x00FF)
            self.bus.write_word_data(self.address, 0x00, reg_swapped)
            self.bus.write_block_data(self.address, 0x03, data)
            logger.debug("Wrote block to register 0x%04X: %s bytes", register, len(data))
        except Exception as e:
            logger.error("Error writing block to register 0x%04X: %s", register, e)
            raise

    def _write_colors(self, colors: List[RGBColor]) -> None:
        color_buf: List[int] = []
        for r, g, b in colors:
            color_buf.extend([r, b, g])

        register = Registers.COLORS_DIRECT_V2 if self.is_direct_mode else Registers.COLORS_EFFECT_V2
        for i in range(0, len(color_buf), 3):
            chunk = color_buf[i : i + 3]
            self._write_register_block(register + i, chunk)

        self.apply()
        if not self.is_direct_mode and self.light_mode == LightMode.STATIC:
            self.save()

    def _set_mode(self, mode: LightMode) -> None:
        if self.is_direct_mode:
            logger.warning("Direct mode is enabled, disable it to set other mode")
        self._write_register(Registers.MODE, mode)
        self.light_mode = mode
        logger.debug("Set mode to %s", mode)

    def _set_direct_mode(self, enabled: bool, color: Optional[RGBColor] = None) -> None:
        if enabled == self.is_direct_mode:
            return
        self._write_register(Registers.DIRECT, 1 if enabled else 0)
        self.is_direct_mode = enabled
        self.set_color(DEFAULT_COLOR if color is None else color)
        self.apply()

    def _get_device_name(self) -> str:
        try:
            name_bytes = self._read_register_block(Registers.DEVICE_NAME, 16)
            return ("".join(chr(byte) for byte in name_bytes)).strip("\x00")
        except Exception as e:
            logger.error("Error reading device name: %s", e)
            return "Unknown"

    def apply(self):
        self._write_register(Registers.APPLY, ApplyMode.APPLY)

    def save(self):
        self._write_register(Registers.APPLY, ApplyMode.SAVE)

    def close(self) -> None:
        try:
            self.bus.close()
            logger.debug("ENE Controller closed")
        except Exception as e:
            logger.error("Error closing ENE Controller: %s", e)
