MEMORY_START_ROM = 0x200
MEMORY_START_INTERNAL = 0xEA0
MEMORY_START_DISPLAY = 0xF00


class Memory:
    def __init__(self) -> None:
        self.memory = bytearray([0] * 4096)
        self.load_fonts()

    def load_fonts(self):
        font_data = [
            0xF0,
            0x90,
            0x90,
            0x90,
            0xF0,
            0x20,
            0x60,
            0x20,
            0x20,
            0x70,
            0xF0,
            0x10,
            0xF0,
            0x80,
            0xF0,
            0xF0,
            0x10,
            0xF0,
            0x10,
            0xF0,
            0x90,
            0x90,
            0xF0,
            0x10,
            0x10,
            0xF0,
            0x80,
            0xF0,
            0x10,
            0xF0,
            0xF0,
            0x80,
            0xF0,
            0x90,
            0xF0,
            0xF0,
            0x10,
            0x20,
            0x40,
            0x40,
            0xF0,
            0x90,
            0xF0,
            0x90,
            0xF0,
            0xF0,
            0x90,
            0xF0,
            0x10,
            0xF0,
            0xF0,
            0x90,
            0xF0,
            0x90,
            0x90,
            0xE0,
            0x90,
            0xE0,
            0x90,
            0xE0,
            0xF0,
            0x80,
            0x80,
            0x80,
            0xF0,
            0xE0,
            0x90,
            0x90,
            0x90,
            0xE0,
            0xF0,
            0x80,
            0xF0,
            0x80,
            0xF0,
            0xF0,
            0x80,
            0xF0,
            0x80,
            0x80,
        ]
        self.memory[0 : len(font_data)] = font_data

    def load_rom(self, rom_data: bytearray) -> None:
        assert MEMORY_START_ROM + len(rom_data) < MEMORY_START_INTERNAL
        for b in rom_data:
            assert 0 <= b < 256
        for i, b in enumerate(rom_data):
            self.memory[MEMORY_START_ROM + i] = b

    def read_op(self, address: int) -> bytearray:
        return self.read_bytes(address, 2)

    def read_bytes(self, address: int, num: int) -> bytearray:
        assert 0 <= address < address + num < 2**12  # 12 bits address
        return self.memory[address : address + num]

    def set_byte(self, address: int, value: int) -> None:
        assert 0 <= address < 2**12  # 12 bits address
        self.memory[address] = value

    def __str__(self) -> str:
        return self.memory.hex(sep="\n", bytes_per_sep=32)
