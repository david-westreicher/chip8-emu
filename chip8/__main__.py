import argparse
from pathlib import Path

from .cpu import CPU, Display
from .memory import Memory

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run rom")
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    rom_file: Path = args.rom
    rom = bytearray(rom_file.read_bytes())
    memory = Memory()
    memory.load_rom(rom)
    display = Display()

    cpu = CPU(memory, display)
    cpu.run()
