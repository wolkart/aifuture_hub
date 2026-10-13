import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import settings as settings_mod  # noqa: E402

TEXT = ("Сейчас покажу одну строку. Без кода, без редактора и бесплатно. "
        "Сервер работает сам. Напиши СЛОВО в комменты, пришлю ссылку.")


def make_words(text=TEXT, step=0.4, gap_after=".", gap=0.8):
    """Слова с предсказуемыми таймингами: каждое 0.3 с, шаг 0.4 с, после точки пауза."""
    out, t = [], 0.2
    for tok in text.split():
        out.append({"text": tok, "start": round(t, 3), "end": round(t + 0.3, 3)})
        t += step + (gap if tok[-1] in gap_after else 0)
    return out


@pytest.fixture
def words():
    return make_words()


@pytest.fixture
def theme():
    return settings_mod.default()["theme"]


@pytest.fixture
def opts():
    return settings_mod.default()["captions"]


@pytest.fixture
def settings_file(tmp_path):
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    (fonts / "Main.ttf").write_bytes(b"main")
    (fonts / "Big.ttf").write_bytes(b"big")
    d = {
        "тема": {"фон_тёмный": ["#101020", "#000000"], "вторичный": "#3366FF", "акцент": "свой",
                 "шрифты": {"основной": "fonts/Main.ttf", "цифры_и_крупно": "fonts/Big.ttf"},
                 "акценты": {"свой": {"градиент": ["#00FFFF", "#AAFF00"], "на_светлом": ["#0088AA", "#448800"]},
                             "плоский": {"на_тёмном": "#FF8800"}}},
        "субтитры": {"стиль": "по_слову", "появление_слова": {"по_умолчанию": "волна"}, "размер_слова_px": 80},
        "музыка": {"трек": "/abs/track.m4a", "рецепт": {"старт": 9.0, "цикл": [20.0, 30.0],
                                                       "тихая_зона_для_конца": [32.0, 40.0], "мин_старт": 4.0}},
        "словарь_замен": {"лего": "СЛОВО"},
        "монтаж": {"наезды": {"уровни": [1.0, 1.2], "вжух": {"плюс": 0.1, "за_с": 0.2}}},
        "папки": {"библиотека_ассетов": "lib", "броллы": "brolls"},
    }
    p = tmp_path / "reel.settings.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture
def clip_mp4(tmp_path_factory):
    """3 с видео 1080×1920 со звуком — для сборки слоёв без рендера."""
    d = tmp_path_factory.mktemp("media")
    out = d / "clip.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=1080x1920:d=3:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:v", "libx264", "-preset",
                    "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out)], check=True)
    return out
