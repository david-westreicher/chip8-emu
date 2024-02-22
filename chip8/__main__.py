import argparse
import logging
from pathlib import Path

from .cpu import CPU
from .data import read_rom
from .gpu_display import GPUDisplay
from .memory import Memory
from .sound import Sound

logging.basicConfig(level=logging.WARNING)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run rom")
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    rom_file: Path = args.rom
    memory = Memory()
    memory.load_rom(read_rom(rom_file))
    display = GPUDisplay()
    sound = Sound()

    cpu = CPU(memory, display, sound)
    cpu.run()
