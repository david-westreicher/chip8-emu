import pytest
from chip8.cpu import CPU
from chip8.display import Display
from chip8.memory import Memory


@pytest.fixture
def cpu() -> CPU:
    memory = Memory()
    display = Display()
    cpu = CPU(memory, display)
    return cpu


@pytest.mark.parametrize("register", "0123456789ABCDE")
def test_instruction_6xnn(cpu: CPU, register: str):
    cpu.execute(bytearray.fromhex(f"6{register}2A"))
    assert cpu.data_registers[int(register, 16)] == 42
