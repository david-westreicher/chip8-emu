import argparse
import logging
import time
from pathlib import Path

import numpy as np

from .cpu import CPU
from .data import read_rom
from .debug import DebugInformation, DebugPipe
from .graphics import Display
from .memory import Memory
from .sound import Sound

np.seterr(over="ignore")
logging.basicConfig(level=logging.WARNING)

TICKS_PER_SECOND = 200

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run rom")
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    rom_file: Path = args.rom
    memory = Memory()
    memory.load_rom(read_rom(rom_file))
    debug_pipe = DebugPipe()
    debug_info = DebugInformation.create_process_synced()
    display = Display(debug_info, debug_pipe)
    sound = Sound()
    cpu = CPU(memory, display, sound, debug_info, debug_pipe)

    while True:
        if -1 in display.pressed_buttons():
            break
        debug_pipe.fetch_messages()
        if not debug_pipe.paused or debug_pipe.open_steps():
            cpu.tick()
        if debug_pipe.should_reset():
            cpu.reset()
            display.clear()
            cpu.tick()
        time.sleep(1 / TICKS_PER_SECOND)

    sound.close()
    display.close()
