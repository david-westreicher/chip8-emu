import numpy as np
import numpy.typing as npt


def display_bytes(data: bytes | bytearray | npt.NDArray[np.uint8 | np.uint16]) -> str:
    if isinstance(data, bytes):
        data = bytearray(data)
    buffer = [hex(b)[2:].zfill(2) for b in data]
    return "|".join(buffer)


def read_address(operation: np.uint16) -> np.uint16:
    return operation & np.uint16(0x0FFF)


def read_byte(operation: np.uint16) -> np.uint8:
    return operation.astype(np.uint8)


def read_half_byte(operation: np.uint16) -> np.uint8:
    return operation.astype(np.uint8) & np.uint8(0xF)
