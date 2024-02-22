import argparse
import logging
from pathlib import Path

from .cpu import CPU, Display
from .data import read_rom
from .memory import Memory

# logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run rom")
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    rom_file: Path = args.rom
    memory = Memory()
    memory.load_rom(read_rom(rom_file))
    display = Display()

    cpu = CPU(memory, display)
    cpu.run()
