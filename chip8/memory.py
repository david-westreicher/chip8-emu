import numpy as np
import numpy.typing as npt

from .data import FONT_DATA

MEMORY_START_ROM = 0x200
MEMORY_START_INTERNAL = 0xEA0
MEMORY_START_DISPLAY = 0xF00


class Memory:
    def __init__(self) -> None:
        self.memory = np.asarray([0] * 4096, dtype=np.uint8)
        self.load_fonts()

    def load_fonts(self) -> None:
        font_data = FONT_DATA
        self.memory[0 : len(font_data)] = font_data

    def load_rom(self, rom_data: npt.NDArray[np.uint8]) -> None:
        assert MEMORY_START_ROM + len(rom_data) < MEMORY_START_INTERNAL
        for b in rom_data:
            assert 0 <= b < 2**8
        for i, b in enumerate(rom_data):
            self.memory[MEMORY_START_ROM + i] = b

    def read_op(self, address: np.uint16) -> np.uint16:
        read_bytes = self.read_bytes(address, np.uint8(2))
        assert len(read_bytes) == 2  # noqa: PLR2004
        return read_bytes.view(np.uint16).byteswap()[0]

    def read_bytes(self, address: np.uint16, num: np.uint8) -> npt.NDArray[np.uint8]:
        assert 0 <= address < address + num < 2**12  # 12 bits address
        return self.memory[address : address + num]

    def set_byte(self, address: np.uint16, value: np.uint8) -> None:
        assert 0 <= address < 2**12  # 12 bits address
        self.memory[address] = value

    def __str__(self) -> str:
        return bytearray(self.memory).hex(sep="\n", bytes_per_sep=32)
