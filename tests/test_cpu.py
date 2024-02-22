from unittest.mock import Mock

import numpy as np
import pytest

from chip8.cpu import CPU


@pytest.fixture()
def cpu() -> CPU:
    memory = Mock()
    display = Mock()
    sound = Mock()
    return CPU(memory, display, sound)


def convert_hex_to_uint16(hex_val: str):
    return np.frombuffer(bytearray.fromhex(hex_val), dtype=np.uint16).byteswap()[0]


@pytest.mark.parametrize("register", "0123456789ABCDE")
def test_instruction_6xnn(cpu: CPU, register: str):
    cpu.execute(convert_hex_to_uint16(f"6{register}2A"))
    assert cpu.data_registers[int(register, 16)] == 42
