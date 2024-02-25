from multiprocessing import Queue
from multiprocessing.managers import SyncManager

INSTRUCTION_PARSING = {
    "0nnn": "SYS addr",
    "00E0": "CLS",
    "00EE": "RET",
    "1nnn": "JP addr",
    "2nnn": "CALL addr",
    "3xkk": "SE Vx: byte",
    "4xkk": "SNE Vx: byte",
    "5xy0": "SE Vx: Vy",
    "6xkk": "LD Vx: byte",
    "7xkk": "ADD Vx: byte",
    "8xy0": "LD Vx: Vy",
    "8xy1": "OR Vx: Vy",
    "8xy2": "AND Vx: Vy",
    "8xy3": "XOR Vx: Vy",
    "8xy4": "ADD Vx: Vy",
    "8xy5": "SUB Vx: Vy",
    "8xy6": "SHR Vx {: Vy}",
    "8xy7": "SUBN Vx: Vy",
    "8xyE": "SHL Vx {: Vy}",
    "9xy0": "SNE Vx: Vy",
    "Annn": "LD I: addr",
    "Bnnn": "JP V0: addr",
    "Cxkk": "RND Vx: byte",
    "Dxyn": "DRW Vx, Vy: nibble",
    "Ex9E": "SKP Vx",
    "ExA1": "SKNP Vx",
    "Fx07": "LD Vx: DT",
    "Fx0A": "LD Vx: K",
    "Fx15": "LD DT: Vx",
    "Fx18": "LD ST: Vx",
    "Fx1E": "ADD I: Vx",
    "Fx29": "LD F: Vx",
    "Fx33": "LD B: Vx",
    "Fx55": "LD [I]: Vx",
    "Fx65": "LD Vx: [I]",
}


class DebugInformation:
    def __init__(self) -> None:
        self.instruction: int = 0
        self.register_I: int = 0
        self.register_DT: int = 0
        self.register_PC: int = 0
        self.data_registers: list[int] = []
        self.stack: list[int] = []

    def update(self, inst: int, i: int, dt: int, pc: int, data_registers: list[int], stack: list[int]) -> None:  # noqa: PLR0913
        self.instruction = inst
        self.register_I = i
        self.register_DT = dt
        self.register_PC = pc
        self.data_registers = data_registers
        self.stack = stack

    def get_instruction(self) -> str:
        inst = hex(self.instruction)[2:].zfill(4).upper()
        fitting_inst = max(
            INSTRUCTION_PARSING,
            key=lambda i: sum(inst[j] == i[j] for j in range(4) if i[j] not in "xykn") if inst[0] == i[0] else -1,
        )
        inst_asm = INSTRUCTION_PARSING[fitting_inst]
        if fitting_inst[1:] == "nnn":
            inst_asm = inst_asm.replace("addr", f"0x{inst[1:].zfill(4)}")
        elif fitting_inst[1:] == "xkk":
            inst_asm = inst_asm.replace("x", inst[1].lower())
            inst_asm = inst_asm.replace("byte", f"0x{inst[2:].zfill(2)}")
        elif fitting_inst[1:] == "xyn":
            inst_asm = inst_asm.replace("x", inst[1].lower())
            inst_asm = inst_asm.replace("y", inst[2].lower())
            inst_asm = inst_asm.replace("nibble", f"0x{inst[3].zfill(2)}")
        elif fitting_inst[1:3] == "xy":
            inst_asm = inst_asm.replace("x", inst[1].lower())
            inst_asm = inst_asm.replace("y", inst[2].lower())
        elif fitting_inst[1] == "x":
            inst_asm = inst_asm.replace("x", inst[1].lower())
        return f"0x{inst} - {inst_asm}"

    def get_register_i(self) -> str:
        return f"0x{hex(self.register_I)[2:].zfill(4).upper()} | {self.register_I}"

    def get_register_pc(self) -> str:
        return f"0x{hex(self.register_PC)[2:].zfill(4).upper()} | {self.register_PC}"

    def get_register_dt(self) -> str:
        return f"0x{hex(self.register_DT)[2:].zfill(4).upper()} | {self.register_DT}"

    def get_data_registers(self) -> str:
        lines = [
            "".join(hex(e)[2:].upper().rjust(8) for e in range(len(self.data_registers))),
            "".join(str(e).rjust(8) for e in self.data_registers),
            "".join(("0x" + hex(e)[2:].upper().zfill(4)).rjust(8) for e in self.data_registers),
        ]
        return "\n".join(lines)

    def get_stack(self) -> list[int]:
        return self.stack

    def __str__(self) -> str:
        return str(self.__dict__)

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def create_process_synced(cls) -> "DebugInformation":
        manager = SyncManager()
        manager.register("DebugInformation", DebugInformation)
        manager.start()
        debug: DebugInformation = manager.DebugInformation()  # type:ignore  # noqa: PGH003
        return debug


class DebugPipe:
    def __init__(self) -> None:
        self.queue_in: "Queue[str]" = Queue()
        self.paused = False
        self.resetted = False
        self.steps = 0

    def pause(self) -> None:
        self.queue_in.put_nowait("pause")
        self.paused = True

    def step(self) -> None:
        self.queue_in.put_nowait("step")
        self.paused = True

    def continue_(self) -> None:
        self.queue_in.put_nowait("continue")
        self.paused = False

    def reset(self) -> None:
        self.queue_in.put_nowait("reset")

    def should_reset(self) -> bool:
        if self.resetted:
            self.resetted = False
            return True
        return False

    def open_steps(self) -> bool:
        if self.steps:
            self.steps -= 1
            return True
        return False

    def fetch_messages(self) -> None:
        while not self.queue_in.empty():
            msg = self.queue_in.get(block=False)
            if not msg:
                continue
            if msg == "pause":
                self.paused = True
            if msg == "continue":
                self.paused = False
            if msg == "reset":
                self.resetted = True
            if msg == "step":
                self.steps += 1
                self.paused = True
