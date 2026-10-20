import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE.parents[1] / "rough-cut" / "scripts"))


def cutlist_doc(keeps, duration, video="/tmp/запись.mp4", fps=(30, 1), audio=None, offset=0.0):
    """cut-list v1 из оставленных кусков [(a, b)] записи длиной duration."""
    import cutlist
    cuts, cur = [], 0.0
    for a, b in keeps:
        if a - cur > 0.02:
            cuts.append({"start": cur, "end": a, "action": "cut", "source": "silence", "reason": "тест"})
        cur = b
    if duration - cur > 0.02:
        cuts.append({"start": cur, "end": duration, "action": "cut", "source": "silence", "reason": "тест"})
    meta = {"scenario": "screencast", "profile": "light", "duration_s": duration, "fps": {"num": fps[0], "den": fps[1]},
            "width": 2940, "height": 1652, "inputs": {"video": video, **({"audio": audio} if audio else {})},
            "sync": {"offset_s": offset}}
    return cutlist.from_cuts(meta, cuts)


@pytest.fixture
def example_words():
    return json.loads((HERE / "fixtures" / "words.example.json").read_text(encoding="utf-8"))
