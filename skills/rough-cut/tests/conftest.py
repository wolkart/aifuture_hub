import math
import random
import struct
import subprocess
import sys
import wave
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

SR = 16000


def write_wav(path, chunks):
    """chunks: [(kind, seconds)], kind ∈ {'tone','silence','noise'}. Детерминированно."""
    rnd = random.Random(42)
    frames = bytearray()
    for kind, sec in chunks:
        for i in range(int(SR * sec)):
            if kind == "tone":
                v = int(12000 * math.sin(2 * math.pi * 440 * i / SR))
            elif kind == "noise":
                v = rnd.randint(-12000, 12000)
            else:
                v = 0
            frames += struct.pack("<h", v)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("media")
    write_wav(d / "tone_gap.wav", [("tone", 1), ("silence", 3), ("tone", 1)])
    write_wav(d / "sync_ref.wav", [("noise", 4)])
    write_wav(d / "sync_shifted.wav", [("silence", 1.5), ("noise", 4)])
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", "testsrc=duration=6:size=320x240:rate=30",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(d / "clip.mp4")],
        check=True)
    return d
