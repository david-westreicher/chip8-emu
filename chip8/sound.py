import wave
from multiprocessing import Process, Queue

import pyaudio

CHUNK = 2048


class Sound:
    def __init__(self) -> None:
        self.queue: "Queue[int]" = Queue()
        p = Process(target=self.sound_loop_task)
        p.start()

    def play(self, value: int) -> None:
        self.queue.put_nowait(value)

    def sound_loop_task(self) -> None:
        wf: wave.Wave_read = wave.open("./sound/chirp.wav")
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )
        data = wf.readframes(CHUNK)
        wf.close()

        while self.queue.get(block=True, timeout=None) + 1:
            stream.write(data)

        # cleanup stuff.
        stream.close()
        p.terminate()
