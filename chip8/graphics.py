import random
import sys
from array import array
from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
from typing import Any

import imgui
import moderngl
import moderngl_window as mglw
import numpy as np
import numpy.typing as npt
from moderngl_window.context.base import KeyModifiers
from moderngl_window.integrations.imgui import ModernglWindowRenderer

from .constants import HEIGHT, WIDTH
from .debug import DebugInformation, DebugPipe

shared_vram = SharedMemory(name="shared_vram", create=True, size=WIDTH * HEIGHT * 3)
keypress_queue: "Queue[tuple[int, str]]" = Queue()
debug_info: DebugInformation = DebugInformation()
debug_pipe = DebugPipe()


class GPUDisplayWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "chip8-emu"
    window_size = (1280, 720)
    aspect_ratio = None

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
        imgui.create_context()
        self.show_debug = False
        self.imgui = ModernglWindowRenderer(self.wnd)
        self.program = self.ctx.program(
            vertex_shader="""
                    #version 330

                    in vec2 in_position;
                    in vec2 in_uv;
                    out vec2 uv;

                    void main() {
                        gl_Position = vec4(in_position, 0.0, 1.0);
                        uv = in_uv;
                    }
                """,
            fragment_shader="""
                    #version 330

                    uniform sampler2D image;
                    in vec2 uv;
                    out vec4 out_color;

                    void main() {
                        // Get the Red, green, blue values from the image
                        vec2 flippedUV = vec2(uv.x, -uv.y);
                        out_color = vec4(texture(image, flippedUV));
                    }
                """,
        )

        self.vertices = self.ctx.buffer(array("f", [-1, 1, 0, 1, -1, -1, 0, 0, 1, 1, 1, 1, 1, -1, 1, 0]))
        self.quad = self.ctx.vertex_array(self.program, [(self.vertices, "2f 2f", "in_position", "in_uv")])
        data = bytearray([random.randint(0, 255) for _ in range(WIDTH) for _ in range(HEIGHT) for _ in range(3)])  # noqa: S311
        self.texture = self.ctx.texture((WIDTH, HEIGHT), 3, data)
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    def render(self, time: float, frame_time: float) -> None:  # noqa: ARG002
        self.ctx.clear(0.0, 0.0, 0.0)
        self.texture.write(shared_vram.buf)
        self.texture.use()
        self.quad.render(moderngl.TRIANGLE_STRIP)
        if self.show_debug:
            self.render_ui()

    def render_ui(self) -> None:
        imgui.new_frame()

        imgui.begin("Debug", True)
        imgui.text(f"PC {debug_info.get_register_pc()}")
        imgui.text(f"OP {debug_info.get_instruction()}")
        imgui.text(f"I  {debug_info.get_register_i()}")
        imgui.text(f"DT {debug_info.get_register_dt()}")
        imgui.text(debug_info.get_data_registers())
        if debug_pipe.paused:
            if imgui.button("Continue"):
                debug_pipe.continue_()
        elif imgui.button("Pause"):
            debug_pipe.pause()
        if imgui.button("Reset"):
            debug_pipe.reset()
        if imgui.button("Step"):
            debug_pipe.step()
        imgui.end()

        imgui.render()
        self.imgui.render(imgui.get_draw_data())

    def resize(self, width: int, height: int) -> None:
        self.imgui.resize(width, height)

    def mouse_position_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self.imgui.mouse_position_event(x, y, dx, dy)

    def mouse_drag_event(self, x: int, y: int, dx: int, dy: int) -> None:
        self.imgui.mouse_drag_event(x, y, dx, dy)

    def mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
        self.imgui.mouse_scroll_event(x_offset, y_offset)

    def mouse_press_event(self, x: int, y: int, button: int) -> None:
        self.imgui.mouse_press_event(x, y, button)

    def mouse_release_event(self, x: int, y: int, button: int) -> None:
        self.imgui.mouse_release_event(x, y, button)

    def unicode_char_entered(self, char: str) -> None:
        self.imgui.unicode_char_entered(char)

    def key_event(self, key: int, action: str, modifiers: KeyModifiers) -> None:
        self.imgui.key_event(key, action, modifiers)
        if key == self.wnd.keys.SPACE and action == self.wnd.keys.ACTION_PRESS:
            self.show_debug = not self.show_debug

        key_map = {
            self.wnd.keys.NUMBER_0: 0,
            self.wnd.keys.NUMBER_1: 1,
            self.wnd.keys.NUMBER_2: 2,
            self.wnd.keys.NUMBER_3: 3,
            self.wnd.keys.NUMBER_4: 4,
            self.wnd.keys.NUMBER_5: 5,
            self.wnd.keys.NUMBER_6: 6,
            self.wnd.keys.NUMBER_7: 7,
            self.wnd.keys.NUMBER_8: 8,
            self.wnd.keys.NUMBER_9: 9,
            self.wnd.keys.A: 0xA,
            self.wnd.keys.B: 0xB,
            self.wnd.keys.C: 0xC,
            self.wnd.keys.D: 0xD,
            self.wnd.keys.E: 0xE,
            self.wnd.keys.F: 0xF,
            self.wnd.keys.ESCAPE: -1,
            self.wnd.keys.Q: -1,
        }
        if key not in key_map:
            return
        keypress_queue.put_nowait((key_map[key], action))
        if key in [self.wnd.keys.Q, self.wnd.keys.ESCAPE]:
            self.wnd.close()


def start_renderer_blocking(
    debug_info_from_main_process: DebugInformation,
    debug_pipe_from_main_process: DebugPipe,
) -> None:
    sys.argv = sys.argv[:1]
    global debug_info, debug_pipe  # noqa: PLW0603
    debug_info = debug_info_from_main_process
    debug_pipe = debug_pipe_from_main_process
    mglw.run_window_config(GPUDisplayWindow)  # type:ignore[]
    shared_vram.close()
    shared_vram.unlink()


class Display:
    def __init__(self, debug_info: DebugInformation, debug_pipe: DebugPipe) -> None:
        self.screen = [[False for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self.button_state: dict[int, str] = {}

        p = Process(target=start_renderer_blocking, args=[debug_info, debug_pipe])
        p.start()

    def show(self) -> None:
        i = 0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                col = 255 if self.screen[y][x] else 0
                shared_vram.buf[i] = col
                i += 1
                shared_vram.buf[i] = col
                i += 1
                shared_vram.buf[i] = col
                i += 1

    def pressed_buttons(self) -> set[int]:
        while not keypress_queue.empty():
            key, action = keypress_queue.get(timeout=1)
            self.button_state[key] = action
        return {k for k, a in self.button_state.items() if a == "ACTION_PRESS"}

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

    def close(self) -> None:
        shared_vram.close()

    def __str__(self) -> str:
        lines = ["+" + "".join("█" if e else " " for e in row) + "+" for row in self.screen]
        top_bot = ["+" * len(lines[0])]
        return "\n".join(top_bot + lines + top_bot)
