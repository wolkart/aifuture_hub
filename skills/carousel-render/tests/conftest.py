import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

CARD_W, CARD_H = 1080, 1350


@pytest.fixture
def theme_dir(tmp_path):
    """Папка темы с минимальным набором файлов."""
    d = tmp_path / "theme"
    (d / "fonts").mkdir(parents=True)
    (d / "assets").mkdir()
    (d / "fonts" / "Oswald.ttf").write_bytes(b"fake-oswald")
    (d / "fonts" / "Montserrat.ttf").write_bytes(b"fake-montserrat")
    (d / "assets" / "avatar-ig.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (d / "assets" / "avatar-li.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    (d / "assets" / "spark.svg").write_text('<svg viewBox="0 0 10 10"/>')
    return d


@pytest.fixture
def theme_file(theme_dir):
    """theme.json рядом с ассетами. Значения нейтральные, не бренд автора."""
    data = {
        "формат": {"ширина": 1080, "высота": 1350, "масштаб_рендера": 2},
        "фоны": {
            "тёмный": {"тип": "radial", "стопы": ["#222147", "#020105"]},
            "светлый": {"тип": "radial", "стопы": ["#FFFFFF", "#E0E9FF"]},
        },
        "цвета": {
            "заголовок_обложки": "#6695F1",
            "акцент": "#D97757",
            "текст_тела": "#33336F",
            "текст_на_тёмном": "#FFFFFF",
            "должность": "#ADADAD",
            "бейдж_на_тёмном": "#E8E7EB",
            "бейдж_кружок_на_светлом": "#33336F",
            "бейдж_текст_на_светлом": "#F7F6FF",
        },
        "шрифты": {
            "файлы": {"oswald": "fonts/Oswald.ttf", "montserrat": "fonts/Montserrat.ttf"},
            "роли": {
                "заголовок_обложки": {"семейство": "Oswald", "вес": 700},
                "подзаголовок_обложки": {"семейство": "Oswald", "вес": 700},
                "текст_тела": {"семейство": "Montserrat", "вес": 500},
                "выделение_тела": {"семейство": "Montserrat", "вес": 700},
                "заголовок_списка": {"семейство": "Montserrat", "вес": 800},
                "подпись_имя": {"семейство": "Montserrat", "вес": 600},
                "подпись_должность": {"семейство": "Montserrat", "вес": 400},
                "бейдж": {"семейство": "Montserrat", "вес": 300},
            },
        },
        "ступени": {
            "обложка_заголовок": [200, 150, 110],
            "обложка_подзаголовок": [56, 48, 40],
            "тело": [60, 52, 44],
            "тело_список": [42, 37, 32],
            "cta": [50, 44, 38],
        },
        "ассеты": {"спарк": "assets/spark.svg"},
        "обвязка": {
            "IG": {
                "аватар": "assets/avatar-ig.png",
                "подпись": ["@your_handle"],
                "позиции": {
                    "обложка": {"бейдж": "верх-центр", "подпись": "низ-лево"},
                    "тело": {"бейдж": "низ-право", "подпись": "низ-лево"},
                    "тело-список": {"бейдж": "низ-право", "подпись": "низ-лево"},
                    "CTA": {"бейдж": "нет", "подпись": "верх-центр"},
                },
            },
            "LI": {
                "аватар": "assets/avatar-li.png",
                "подпись": ["Your Name", "Role & Tagline"],
                "позиции": {
                    "обложка": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "тело": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "тело-список": {"бейдж": "верх-центр", "подпись": "низ-центр"},
                    "CTA": {"бейдж": "нет", "подпись": "верх-центр"},
                },
            },
        },
    }
    p = theme_dir / "theme.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p
