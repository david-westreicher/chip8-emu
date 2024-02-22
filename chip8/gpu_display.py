import random
import sys
from array import array
from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
from typing import Any

import moderngl
import moderngl_window as mglw
from moderngl_window.context.base import KeyModifiers

from .constants import HEIGHT, WIDTH
from .display import Display

shared_vram = SharedMemory(name="shared_vram", create=True, size=WIDTH * HEIGHT * 3)
keypress_queue: "Queue[tuple[int, str]]" = Queue()


class GPUDisplayWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "chip8-emu"
    window_size = (1280, 720)

    def __init__(self, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(**kwargs)
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

    def key_event(self, key: int, action: str, modifiers: KeyModifiers) -> None:  # noqa: ARG002
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


def start_renderer_blocking() -> None:
    sys.argv = sys.argv[:1]
    mglw.run_window_config(GPUDisplayWindow)  # type:ignore[]
    shared_vram.close()
    shared_vram.unlink()


class GPUDisplay(Display):
    def __init__(self) -> None:
        super().__init__()
        p = Process(target=start_renderer_blocking)
        p.start()
        self.button_state: dict[int, str] = {}

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

    def close(self) -> None:
        shared_vram.close()
