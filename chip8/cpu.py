import logging
import random
import time

import keyboard

from .display import Display
from .memory import MEMORY_START_ROM, Memory

# https://colineberhardt.github.io/wasm-rust-chip8/web/
# http://devernay.free.fr/hacks/chip8/C8TECH10.HTM


KEY_MAP = {
    0x00: "0",
    0x01: "1",
    0x02: "2",
    0x03: "3",
    0x04: "4",
    0x05: "5",
    0x06: "6",
    0x07: "7",
    0x08: "8",
    0x09: "9",
    0x0A: "a",
    0x0B: "b",
    0x0C: "c",
    0x0D: "d",
    0x0E: "e",
}


class CPU:
    def __init__(self, memory: Memory, display: Display) -> None:
        self.memory = memory
        self.display = display

        self.data_registers = bytearray([0] * 16)
        self.register_I = 0  # 12 bits
        self.register_DT = 0  # 12 bits
        self.register_PC = MEMORY_START_ROM  # 12 bits
        self.stack = []

    def run(self):
        while True:
            # os.system("clear")
            operation = self.fetch()
            # print(self)
            print(self.display)
            # print(operation.hex())
            self.execute(operation)
            time.sleep(0.01)

    def fetch(self):
        return self.memory.read_op(self.register_PC)

    def execute(self, operation: bytearray):
        hex_repr = operation.hex()
        match tuple(hex_repr):
            case ("0", "0", "e", "0"):
                # 00E0 - CLS                                - Clear the display.
                self.display.clear()
                self.register_PC += 2
            case ("0", "0", "e", "e"):
                # 00EE - RET                                - Return from a subroutine.
                self.register_PC = self.stack.pop()
                self.register_PC += 2
            case ("1", *addr):
                # 1nnn - JP addr                            - Jump to location nnn.
                value = int("".join(addr), 16)
                self.register_PC = value
            case ("2", *addr):
                # 2nnn - CALL addr                          - Call subroutine at nnn.
                self.stack.append(self.register_PC)
                address = int("".join(addr), 16)
                self.register_PC = address
            case ("3", vx, *byte):
                # 3xkk - SE Vx, byte                        - Skip next instruction if Vx = kk.
                value = self.get_register(vx)
                if value == int("".join(byte), 16):
                    self.register_PC += 2
                self.register_PC += 2
            case ("4", vx, *byte):
                # 4xkk - SNE Vx, byte                       - Skip next instruction if Vx != kk.
                value = self.get_register(vx)
                if value != int("".join(byte), 16):
                    self.register_PC += 2
                self.register_PC += 2
            case ("5", vx, vy, "0"):
                # 5xy0 - SE Vx, Vy                          - Skip next instruction if Vx = Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                if value_1 == value_2:
                    self.register_PC += 2
                self.register_PC += 2
            case ("6", vx, *byte):
                # 6xkk - LD Vx, byte                        - Set Vx = kk.
                self.set_register(vx, int("".join(byte), 16))
                self.register_PC += 2
            case ("7", vx, *byte):
                # 7xkk - ADD Vx, byte                       - Set Vx = Vx + kk.
                value = self.get_register(vx)
                value += int("".join(byte), 16)
                value %= 2**8
                self.set_register(vx, value)
                self.register_PC += 2
            case ("8", vx, vy, "0"):
                # 8xy2 - AND Vx, Vy                         - Set Vx = Vx AND Vy.
                value_2 = self.get_register(vy)
                self.set_register(vx, value_2)
                self.register_PC += 2
            case ("8", vx, vy, "2"):
                # 8xy2 - AND Vx, Vy                         - Set Vx = Vx AND Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 & value_2
                self.set_register(vx, value)
                self.register_PC += 2
            case ("8", vx, vy, "4"):
                # 8xy4 - ADD Vx, Vy                         - Set Vx = Vx + Vy, set VF = carry.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                value = value_1 + value_2
                if value > 255:
                    self.set_register("f", 1)
                else:
                    self.set_register("f", 0)
                value %= 2**8
                self.set_register(vx, value)
                self.register_PC += 2
            case ("8", vx, _, "6"):
                # 8xy6 - SHR Vx {, Vy}                      - Set Vx = Vx SHR 1.
                value = self.get_register(vx)
                if value & 1:
                    self.set_register("f", 1)
                else:
                    self.set_register("f", 0)
                value //= 2
                self.set_register(vx, value)
                self.register_PC += 2
            case ("8", vx, _, "e"):
                # 8xyE - SHL Vx {, Vy}                      - Set Vx = Vx SHL 1.
                value = self.get_register(vx)
                if value & 2**7:
                    self.set_register("f", 1)
                else:
                    self.set_register("f", 0)
                value *= 2
                value %= 2**8
                self.set_register(vx, value)
                self.register_PC += 2
            case ("9", vx, vy, "0"):
                # 9xy0 - SNE Vx, Vy                         - Skip next instruction if Vx != Vy.
                value_1 = self.get_register(vx)
                value_2 = self.get_register(vy)
                if value_1 != value_2:
                    self.register_PC += 2
                self.register_PC += 2
            case ("a", *addr):
                # Annn - LD I, addr                         - Set I = nnn
                self.register_I = int("0" + "".join(addr), 16)
                self.register_PC += 2
            case ("c", vx, *byte):
                # Cxkk - RND Vx, byte                       - Set Vx = random byte AND kk.
                rnd = random.randint(0, 255)
                value = rnd & int("".join(byte), 16)
                self.set_register(vx, value)
                self.register_PC += 2
            case ("d", vx, vy, nibble):
                # Dxyn - DRW Vx, Vy, nibble                 - Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision
                coord_x = self.get_register(vx)
                coord_y = self.get_register(vy)
                graphic_data = self.memory.read_bytes(self.register_I, int(nibble, 16))
                erased = self.display.blit(coord_x, coord_y, graphic_data)
                self.set_register("f", 1 if erased else 0)
                self.register_PC += 2
            case ("e", vx, "9", "e"):
                # Ex9E - SKP Vx                             - Skip next instruction if key with the value of Vx is pressed.
                value = self.get_register(vx)
                if self.is_pressed(value):
                    self.register_PC += 2
                self.register_PC += 2
            case ("e", vx, "a", "1"):
                # ExA1 - SKNP Vx                            - Skip next instruction if key with the value of Vx is not pressed.
                value = self.get_register(vx)
                if not self.is_pressed(value):
                    self.register_PC += 2
                self.register_PC += 2
            case ("f", vx, "0", "7"):
                value = self.register_DT
                self.set_register(vx, value)
                self.register_PC += 2
            case ("f", vx, "0", "a"):
                value = self.wait_for_and_parse_input()
                self.set_register(vx, value)
                self.register_PC += 2
            case ("f", vx, "1", "5"):
                # Fx15 - LD DT, Vx                          - Set delay timer = Vx.
                # TODO: implement sound
                logging.warning("Delay timer not implemented")
                self.register_PC += 2
            case ("f", vx, "1", "8"):
                # Fx18 - LD ST, Vx                          - Set sound timer = Vx.
                # TODO: implement sound
                logging.warning("Sound timer not implemented")
                self.register_PC += 2
            case ("f", vx, "1", "e"):
                # Fx1E - ADD I, Vx                          - Set I = I + Vx.
                self.register_I += self.get_register(vx)
                self.register_PC += 2
            case ("f", vx, "2", "9"):
                # Fx29 - LD F, Vx                           - Set I = location of sprite for digit Vx.
                sprite_num = self.get_register(vx)
                self.register_I = sprite_num * 5
                self.register_PC += 2
            case ("f", vx, "3", "3"):
                # Fx33 - LD B, Vx                           - Store BCD representation of Vx in memory locations I, I+1, and I+2.
                value = self.get_register(vx)
                self.memory.set_byte(self.register_I + 2, value % 10)
                value //= 10
                self.memory.set_byte(self.register_I + 1, value % 10)
                value //= 10
                self.memory.set_byte(self.register_I + 0, value % 10)
                self.register_PC += 2
            case ("f", vx, "5", "5"):
                # Fx65 - LD Vx, [I]                         - Read registers V0 through Vx from memory starting at location I.
                for i in range(int(vx, 16)):
                    self.memory.set_byte(self.register_I + i, self.get_register(hex(i)))
                self.register_PC += 2
            case ("f", vx, "6", "5"):
                # Fx65 - LD Vx, [I]                         - Read registers V0 through Vx from memory starting at location I.
                for i in range(int(vx, 16)):
                    self.set_register(
                        hex(i),
                        int.from_bytes(self.memory.read_bytes(self.register_I + i, 1)),
                    )
                self.register_PC += 2
            case _:
                raise NotImplementedError(hex_repr)

    def is_pressed(self, key_num: int):
        # TODO: implement
        return keyboard.is_pressed(KEY_MAP[key_num])

    def get_register(self, reg: str) -> int:
        register_num = int(reg, 16)
        return self.data_registers[register_num]

    def wait_for_and_parse_input(self) -> int:
        # TODO return correct character code
        char = input()
        return 1

    def set_register(self, reg: str, data: int):
        assert 0 <= data < 2**8
        register_num = int(reg, 16)
        self.data_registers[register_num] = data

    def __str__(self):
        return f"PC: {self.register_PC}, I: {self.register_I}, regs: {self.data_registers.hex(sep='|')}"
