import logging
from typing import List, TypeAlias

RGBColor: TypeAlias = tuple[int, int, int]
DEFAULT_COLOR: RGBColor = (15, 0, 0)
DISABLED_COLOR: RGBColor = (0, 0, 0)

CommandData: TypeAlias = str | bytes | bytearray | List[int]
logger = logging.getLogger(__name__)


def _convert_to_bytes(data: CommandData) -> bytes:
    if isinstance(data, str):
        return bytes.fromhex(data.replace(" ", ""))
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, list):
        return bytes(data)

    raise ValueError(f"Unsupported data type: {type(data)}")


def normalize_command_data(command_data: CommandData, packet_size: int, prefix: CommandData | None = None) -> bytes:
    data = _convert_to_bytes(command_data)

    if prefix is not None:
        data = _convert_to_bytes(prefix) + data

    if len(data) < packet_size:
        data = data + b"\x00" * (packet_size - len(data))
    elif len(data) > packet_size:
        data = data[:packet_size]

    return data


def format_hex(data: bytes | int, trim_zeros: bool = True) -> str:
    if isinstance(data, int):
        data = bytes(data)

    if trim_zeros:
        trimmed_data = data.rstrip(b"\x00")
        if not trimmed_data:
            trimmed_data = data[:1] if data else b""
    else:
        trimmed_data = data

    return " ".join(f"{byte:02X}" for byte in trimmed_data)
