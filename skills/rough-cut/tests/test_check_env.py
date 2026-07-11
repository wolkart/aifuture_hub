import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_env  # noqa: E402


def test_whisper_backend_apple_silicon():
    assert check_env.whisper_backend("darwin", "arm64") == "mlx-whisper"


def test_whisper_backend_other_platforms():
    assert check_env.whisper_backend("darwin", "x86_64") == "faster-whisper"
    assert check_env.whisper_backend("linux", "x86_64") == "faster-whisper"
    assert check_env.whisper_backend("win32", "AMD64") == "faster-whisper"


def test_report_structure():
    r = check_env.report()
    assert set(r) >= {"ok", "platform", "whisper_backend", "whisper_note", "missing"}
    for m in r["missing"]:
        assert m["name"] and m["install"]


def test_cli_json_on_bare_python():
    """Доктор обязан работать на голом python3 без сторонних пакетов."""
    p = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_env.py"), "--json"],
        capture_output=True, text=True)
    assert p.returncode == 0
    data = json.loads(p.stdout)
    assert isinstance(data["ok"], bool)
