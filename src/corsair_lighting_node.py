import logging
import threading
import time
from enum import IntEnum
from itertools import chain
from typing import List, Optional

import hid

from led_controller_interface import LEDController
from utils import DEFAULT_COLOR, DISABLED_COLOR, CommandData, RGBColor, format_hex, normalize_command_data

logger = logging.getLogger(__name__)

MAX_LED_NUMBER = 204


class CommandId(IntEnum):
    WRITE_LED_COLOR_VALUES = 0x32
    WRITE_LED_TRIGGER = 0x33
    WRITE_LED_CLEAR = 0x34
    WRITE_LED_GROUP_SET = 0x35
    WRITE_LED_GROUPS_CLEAR = 0x37
    WRITE_LED_MODE = 0x38
    WRITE_LED_BRIGHTNESS = 0x39
    WRITE_LED_COUNT = 0x3A
    WRITE_LED_PORT_TYPE = 0x3B
    WRITE_LED_START_AUTODETECTION = 0x3C
    READ_LED_AUTODETECTION_RESULTS = 0x3D


class RGBChannel(IntEnum):
    RED = 0x00
    GREEN = 0x01
    BLUE = 0x02


class ChannelMode(IntEnum):
    DISABLED = 0x00
    HARDWARE = 0x01
    SOFTWARE = 0x02


class LEDSpeed(IntEnum):
    FAST = 0x01
    MEDIUM = 0x01
    SLOW = 0x02


class LEDMode(IntEnum):
    RAINBOW = 0x00
    COLOR_SHIFT = 0x01
    COLOR_PULSE = 0x02
    COLOR_WAVE = 0x03
    FIXED = 0x04
    # TEMPERATURE = 0x05
    VISOR = 0x06
    MARQUEE = 0x07
    BLINK = 0x08
    SEQUENTIAL = 0x09
    RAINBOW2 = 0x0A


class LEDDirection(IntEnum):
    BACKWARD = 0x01
    FORWARD = 0x00


class CorsairLightingNodeController(LEDController):
    VENDOR_ID = 0x1B1C
    PRODUCT_ID = 0x0C1A
    WRITE_PACKET_SIZE = 65
    READ_PACKET_SIZE = 17
    READ_TIMEOUT = 15
    LED_COUNT = 4 * 8
    CHANNEL = 0

    def __init__(self) -> None:
        self.device: Optional[hid.Device] = None
        self.working_mode: ChannelMode = ChannelMode.DISABLED
        self.keepalive_thread: Optional[threading.Thread] = None
        self.keepalive_running = False
        self.last_commit_time = time.time()
        self.lock = threading.Lock()

    def set_static_color(self, color: RGBColor):
        self._apply_led_mode(LEDMode.FIXED, [color])

    def turn_on(self) -> None:
        self._connect()
        logger.info("Turning on CORSAIR Lighting Node CORE")
        self.set_static_color(DEFAULT_COLOR)

    def turn_off(self) -> None:
        logger.info("Turning off CORSAIR Lighting Node CORE")
        self.set_static_color(DISABLED_COLOR)
        self._disconnect()

    def set_rainbow_effect(self, speed: LEDSpeed):
        self._apply_led_mode(LEDMode.RAINBOW, None, speed)

    def _connect(self) -> None:
        try:
            self.device = hid.Device(vid=self.VENDOR_ID, pid=self.PRODUCT_ID)
            logger.info("Connected to CORSAIR Lighting Node CORE")
        except OSError as os_err:
            logger.error(
                "Failed to connect to CORSAIR Lighting Node CORE - device not found or access denied: %s", os_err
            )
            raise
        except ValueError as val_err:
            logger.error("Invalid device parameters: %s", val_err)
            raise

    def _disconnect(self) -> None:
        if self.device:
            try:
                self.device.close()
            except OSError as e:
                logger.warning("Error closing device (may already be closed): %s", e)
            finally:
                self.device = None

        logger.info("CORSAIR Lighting Node CORE disconnected")

    def _send_command(self, command_data: CommandData) -> int | bytes:
        if not self.device:
            raise RuntimeError("Device not opened")
        try:
            data = normalize_command_data(command_data, self.WRITE_PACKET_SIZE, [0x00])
            logger.debug("Sending command: %s", format_hex(data))

            bytes_written = self.device.write(data)
            if bytes_written == 0:
                raise OSError("Failed to write data to device")

            try:
                response = self.device.read(self.READ_PACKET_SIZE, timeout=self.READ_TIMEOUT)
                if not response and command_data[0] != CommandId.WRITE_LED_GROUPS_CLEAR:
                    logger.warning("Device returned empty response (CommandID: 0x%02X)", command_data[0])
                return response
            except OSError as e:
                logger.error("Failed to read from device: %s", e)
                raise
        except Exception as e:
            logger.error("Error sending command: %s", e)
            raise

    def _switch_to_software_mode(self):
        if self.working_mode is ChannelMode.SOFTWARE:
            return

        self._write_led_mode(ChannelMode.SOFTWARE)

    def _apply_led_mode(
        self,
        mode: LEDMode,
        colors: Optional[List[RGBColor]] = None,
        speed: LEDSpeed = LEDSpeed.MEDIUM,
        direction: LEDDirection = LEDDirection.FORWARD,
        start_led: int = 0,
        num_leds: Optional[int] = MAX_LED_NUMBER,
    ) -> None:
        self._write_groups_clear()
        self._write_led_clear()
        self._write_led_mode(ChannelMode.HARDWARE)
        self._write_led_group_set(mode, colors, speed, direction, start_led, num_leds)
        self._write_led_trigger()

    def _write_groups_clear(self):
        self._send_command([CommandId.WRITE_LED_GROUPS_CLEAR])

    def _write_led_clear(self):
        self._send_command([CommandId.WRITE_LED_CLEAR])

    def _write_led_mode(self, mode: ChannelMode):
        self._send_command([CommandId.WRITE_LED_MODE, self.CHANNEL, mode])

    def _write_led_group_set(
        self,
        mode: LEDMode,
        colors: Optional[List[RGBColor]] = None,
        speed: LEDSpeed = LEDSpeed.MEDIUM,
        direction: LEDDirection = LEDDirection.FORWARD,
        start_led: int = 0,
        num_leds: Optional[int] = None,
    ):
        if colors is None:
            colors = []
        if num_leds is None:
            num_leds = self.LED_COUNT

        random_colors = 0x00 if mode == LEDMode.FIXED or len(colors) != 0 else 0x01

        response = self._send_command(
            [
                CommandId.WRITE_LED_GROUP_SET,
                self.CHANNEL,
                start_led,
                num_leds,
                mode,
                speed,
                direction,
                random_colors,
                0xFF,
                *chain.from_iterable(colors),
            ]
        )
        logger.debug("RESPONSE WRITE_LED_GROUP_SET: %s", format_hex(response))

    def _write_led_trigger(self) -> None:
        self._send_command([CommandId.WRITE_LED_TRIGGER, 0xFF])
        self.last_commit_time = time.time()

    def _write_led_color_values(self, start: int, count: int, color_channel: RGBChannel, color_data: List[int]) -> None:
        if start < 0 or count <= 0 or start + count > self.LED_COUNT:
            raise ValueError(f"Invalid LED range: start={start}, count={count}, max={self.LED_COUNT}")

        packet = [CommandId.WRITE_LED_COLOR_VALUES, self.CHANNEL, start, count, color_channel]
        packet.extend(color_data[:count])
        self._send_command(packet)
