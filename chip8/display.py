import numpy as np
import numpy.typing as npt


class Display:
    def __init__(self) -> None:
        self.screen = [[False for _ in range(64)] for _ in range(32)]

    def blit(self, x: np.uint8, y: np.uint8, graphic_data: npt.NDArray[np.uint8]) -> bool:
        erased = False
        for i, b in enumerate(graphic_data):
            for j, bit in enumerate(bin(b)[2:].zfill(8)):
                y_coord = (y + i) % len(self.screen)
                x_coord = (x + j) % len(self.screen[0])
                before = self.screen[y_coord][x_coord]
                self.screen[y_coord][x_coord] ^= bit == "1"
                now = self.screen[y_coord][x_coord]
                if before and not now:
                    erased = True
        return erased

    def clear(self) -> None:
        self.screen = [[False for _ in range(64)] for _ in range(32)]

    def show(self) -> None:
        print(self)  # noqa: T201

    def __str__(self) -> str:
        lines = ["+" + "".join("█" if e else " " for e in row) + "+" for row in self.screen]
        top_bot = ["+" * len(lines[0])]
        return "\n".join(top_bot + lines + top_bot)
