# https://colineberhardt.github.io/wasm-rust-chip8/web/
# http://devernay.free.fr/hacks/chip8/C8TECH10.HTM

import logging
import random

import numpy as np

from .debug import DebugInformation, DebugPipe
from .graphics import Display
from .memory import MEMORY_START_ROM, Memory
from .sound import Sound
from .utils import display_bytes, read_address, read_byte, read_half_byte


class CPU:
    def __init__(  # noqa: PLR0913
        self,
        memory: Memory,
        display: Display,
        sound: Sound,
        debug_info: DebugInformation,
        debug_pipe: DebugPipe,
    ) -> None:
        self.memory = memory
        self.display = display
        self.sound = sound
        self.debug_info = debug_info
        self.debug_pipe = debug_pipe

        self.data_registers = np.asarray([0] * 16, np.uint8)
        self.register_I = np.uint16(0)  # 12 bits
        self.register_DT = np.uint8(0)  # 12 bits
        self.register_PC = np.uint16(MEMORY_START_ROM)  # 12 bits
        self.stack: list[np.uint16] = []
        self.wait_for_input_reg: str = ""

    def tick(self) -> None:
        operation = self.fetch()
        logging.info(self)
        logging.info(("Operation", hex(operation)[2:].zfill(4)))
        self.pressed_buttons = self.display.pressed_buttons()
        self.debug_info.update(
            int(operation),
            int(self.register_I),
            int(self.register_DT),
            int(self.register_PC),
            [int(v) for v in self.data_registers],
            [int(v) for v in self.stack],
        )
        if self.wait_for_input_reg:
            if not self.pressed_buttons:
                return
            val = np.uint8(next(iter(self.pressed_buttons)))
            self.set_register(self.wait_for_input_reg, val)
            self.register_PC += np.uint16(2)
            self.wait_for_input_reg = ""
        else:
            self.execute(operation)
        self.display.show()

        if self.register_DT > 0:
            self.register_DT -= np.uint8(1)

    def fetch(self) -> np.uint16:
        return self.memory.read_op(self.register_PC)

    def execute(self, operation: np.uint16) -> None:  # noqa: C901, PLR0912, PLR0915
        hex_repr = hex(int(operation))[2:].zfill(4)
        match tuple(hex_repr):
            case ("0", "0", "e", "0"):
                # 00E0 - CLS                                - Clear the display.
                self.display.clear()
                self.register_PC += np.uint16(2)
            case ("0", "0", "e", "e"):
                # 00EE - RET                                - Return from a subroutine.
                self.register_PC = self.stack.pop()
                self.register_PC += np.uint16(2)
            case ("0", *_):
                # 0nnn - SYS addr                           - Jump to a machine code routine at nnn.
                logging.warning("Ignore old instruction 0nnn")
                self.register_PC += np.uint16(2)
            case ("1", *_):
                # 1nnn - JP addr                            - Jump to location nnn.
                self.register_PC = read_address(operation)
            case ("2", *_):
                # 2nnn - CALL addr                          - Call subroutine at nnn.
                self.stack.append(self.register_PC)
                self.register_PC = read_address(operation)
            case ("3", vx, *_):
                # 3xkk - SE Vx, byte                        - Skip next instruction if Vx = kk.
                value = self.get_register(vx)
                if value == read_byte(operation):
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("4", vx, *_):
                # 4xkk - SNE Vx, byte                       - Skip next instruction if Vx != kk.
                value = self.get_register(vx)
                if value != read_byte(operation):
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("5", vx, vy, "0"):
                # 5xy0 - SE Vx, Vy                          - Skip next instruction if Vx = Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                if value_1 == value_2:
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("6", vx, *_):
                # 6xkk - LD Vx, byte                        - Set Vx = kk.
                self.set_register(vx, read_byte(operation))
                self.register_PC += np.uint16(2)
            case ("7", vx, *_):
                # 7xkk - ADD Vx, byte                       - Set Vx = Vx + kk.
                value = self.get_register(vx)
                value += read_byte(operation)
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "0"):
                # 8xy2 - AND Vx, Vy                         - Set Vx = Vx AND Vy.
                value_2 = self.get_register(vy)
                self.set_register(vx, value_2)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "1"):
                # 8xy2 - OR Vx, Vy                         - Set Vx = Vx OR Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 | value_2
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "2"):
                # 8xy2 - AND Vx, Vy                         - Set Vx = Vx AND Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 & value_2
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "3"):
                # 8xy3 - XOR Vx, Vy                       - Set Vx = Vx XOR Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 ^ value_2
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "4"):
                # 8xy4 - ADD Vx, Vy                         - Set Vx = Vx + Vy, set VF = carry.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 + value_2
                if int(value_1) + int(value_2) >= 2**8:
                    self.set_register("f", np.uint8(1))
                else:
                    self.set_register("f", np.uint8(0))
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "5"):
                # 8xy5 - SUB Vx, Vy                         - Set Vx = Vx - Vy, set VF = NOT borrow.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 - value_2
                if int(value_1) > int(value_2):
                    self.set_register("f", np.uint8(1))
                else:
                    self.set_register("f", np.uint8(0))
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, _, "6"):
                # 8xy6 - SHR Vx {, Vy}                      - Set Vx = Vx SHR 1.
                value = self.get_register(vx)
                if value & 1:
                    self.set_register("f", np.uint8(1))
                else:
                    self.set_register("f", np.uint8(0))
                value //= 2
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, vy, "7"):
                # 8xy7 - SUBN Vx, Vy                        - Set Vx = Vy - Vx, set VF = NOT borrow.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_2 - value_1
                if int(value_2) > int(value_1):
                    self.set_register("f", np.uint8(1))
                else:
                    self.set_register("f", np.uint8(0))
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("8", vx, _, "e"):
                # 8xyE - SHL Vx {, Vy}                      - Set Vx = Vx SHL 1.
                value = self.get_register(vx)
                if value & 2**7:
                    self.set_register("f", np.uint8(1))
                else:
                    self.set_register("f", np.uint8(0))
                value *= 2
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("9", vx, vy, "0"):
                # 9xy0 - SNE Vx, Vy                         - Skip next instruction if Vx != Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                if value_1 != value_2:
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("a", *_):
                # Annn - LD I, addr                         - Set I = nnn
                self.register_I = read_address(operation)
                self.register_PC += np.uint16(2)
            case ("c", vx, *_):
                # Cxkk - RND Vx, byte                       - Set Vx = random byte AND kk.
                rnd = np.uint8(random.randint(0, 255))  # noqa: S311
                value = rnd & read_byte(operation)
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("d", vx, vy, _):
                # Dxyn - DRW Vx, Vy, nibble                 - Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision  # noqa: E501
                coord_x = self.get_register(vx)
                coord_y = self.get_register(vy)
                graphic_data = self.memory.read_bytes(self.register_I, read_half_byte(operation))
                erased = self.display.blit(coord_x, coord_y, graphic_data)
                self.set_register("f", np.uint8(1 if erased else 0))
                self.register_PC += np.uint16(2)
            case ("e", vx, "9", "e"):
                # Ex9E - SKP Vx                             - Skip next instruction if key with the value of Vx is pressed.  # noqa: E501
                value = self.get_register(vx)
                if self.is_pressed(value):
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("e", vx, "a", "1"):
                # ExA1 - SKNP Vx                            - Skip next instruction if key with the value of Vx is not pressed.  # noqa: E501
                value = self.get_register(vx)
                if not self.is_pressed(value):
                    self.register_PC += np.uint16(2)
                self.register_PC += np.uint16(2)
            case ("f", vx, "0", "7"):
                # Fx07 - LD Vx, DT                          - Set Vx = delay timer value.
                value = self.register_DT
                self.set_register(vx, value)
                self.register_PC += np.uint16(2)
            case ("f", vx, "0", "a"):
                # Fx0A - LD Vx, K                           - Wait for a key press, store the value of the key in Vx.
                self.wait_for_input_reg = vx
            case ("f", vx, "1", "5"):
                # Fx15 - LD DT, Vx                          - Set delay timer = Vx.
                self.register_DT = self.get_register(vx)
                self.register_PC += np.uint16(2)
            case ("f", vx, "1", "8"):
                # Fx18 - LD ST, Vx                          - Set sound timer = Vx.
                # TODO: implement sound correctly
                value = self.get_register(vx)
                self.sound.play(int(value))
                self.register_PC += np.uint16(2)
            case ("f", vx, "1", "e"):
                # Fx1E - ADD I, Vx                          - Set I = I + Vx.
                self.register_I += self.get_register(vx)
                self.register_PC += np.uint16(2)
            case ("f", vx, "2", "9"):
                # Fx29 - LD F, Vx                           - Set I = location of sprite for digit Vx.
                sprite_num = self.get_register(vx)
                self.register_I = np.uint16(sprite_num * 5)
                self.register_PC += np.uint16(2)
            case ("f", vx, "3", "3"):
                # Fx33 - LD B, Vx                           - Store BCD representation of Vx in memory locations I, I+1, and I+2.  # noqa: E501
                value = int(self.get_register(vx))
                self.memory.set_byte(self.register_I + np.uint16(2), np.uint8(value % 10))
                value //= 10
                self.memory.set_byte(self.register_I + np.uint16(1), np.uint8(value % 10))
                value //= 10
                self.memory.set_byte(self.register_I + np.uint16(0), np.uint8(value % 10))
                self.register_PC += np.uint16(2)
            case ("f", vx, "5", "5"):
                # Fx55 - LD [I], Vx                         - Store registers V0 through Vx in memory starting at location I.  # noqa: E501
                for i in range(int(vx, 16) + 1):
                    self.memory.set_byte(self.register_I + np.uint16(i), self.get_register(hex(i)))
                self.register_PC += np.uint16(2)
            case ("f", vx, "6", "5"):
                # Fx65 - LD Vx, [I]                         - Read registers V0 through Vx from memory starting at location I.  # noqa: E501
                for i in range(int(vx, 16) + 1):
                    read_bytes = self.memory.read_bytes(self.register_I + np.uint16(i), np.uint8(1))
                    self.set_register(hex(i), read_bytes[0])
                self.register_PC += np.uint16(2)
            case _:
                raise NotImplementedError(hex_repr)

    def is_pressed(self, key_num: np.uint8) -> bool:
        return bool(key_num in self.pressed_buttons)

    def get_register(self, reg: str) -> np.uint8:
        register_num = int(reg, 16)
        return self.data_registers[register_num]

    def set_register(self, reg: str, data: np.uint8) -> None:
        assert 0 <= data < 2**8
        register_num = int(reg, 16)
        self.data_registers[register_num] = data

    def reset(self) -> None:
        self.data_registers.fill(np.uint8(0))
        self.register_I = np.uint16(0)
        self.register_DT = np.uint8(0)
        self.register_PC = np.uint16(MEMORY_START_ROM)
        self.stack.clear()
        self.wait_for_input_reg = ""

    def __str__(self) -> str:
        return f"PC: {self.register_PC, hex(self.register_PC)}, I: {self.register_I}, regs: {display_bytes(self.data_registers)}"  # noqa: E501
