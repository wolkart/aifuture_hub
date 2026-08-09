#!/usr/bin/env python3
"""Загрузка и проверка темы карусели. Только stdlib.

Тема — единственное место, где живут переменные внешнего вида. Композиция
лейаутов в коде, поэтому сюда нельзя добавить «ещё один шаблон»: сюда
добавляют значения.
"""
import argparse
import json
from pathlib import Path

LAYOUTS = ("обложка", "тело", "тело-список", "промпт", "CTA")
PLATFORMS = ("IG", "LI")

REQUIRED_COLORS = ("заголовок_обложки", "акцент", "текст_тела",
                   "текст_на_тёмном", "должность", "бейдж_на_тёмном",
                   "бейдж_кружок_на_светлом", "бейдж_текст_на_светлом")
REQUIRED_ROLES = ("заголовок_обложки", "подзаголовок_обложки", "текст_тела",
                  "выделение_тела", "заголовок_списка", "подпись_имя",
                  "подпись_должность", "бейдж")
REQUIRED_STEPS = ("обложка_заголовок", "обложка_подзаголовок", "тело",
                  "тело_список", "cta")
STEP_COUNT = 3

# Ступени для лейаутов, появившихся позже темы автора. Требовать их в теме
# нельзя: это сломало бы все существующие темы на ровном месте. Задал у себя —
# твои значения побеждают, не задал — работает на этих.
DEFAULT_STEPS = {"промпт": [30, 26, 23]}

# Обвязка по умолчанию под лейаут, которого нет в теме. У плотной карточки
# бейдж и подпись уходят вниз: сверху им негде стоять, там текст.
DEFAULT_POSITIONS = {"промпт": {"бейдж": "низ-право", "подпись": "низ-лево"}}


def load(path):
    """Читает theme.json и делает пути ассетов абсолютными."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    data["_dir"] = base

    for key, rel in data.get("шрифты", {}).get("файлы", {}).items():
        data["шрифты"]["файлы"][key] = base / rel
    for key, rel in data.get("ассеты", {}).items():
        data["ассеты"][key] = base / rel
    for platform in data.get("обвязка", {}).values():
        if "аватар" in platform:
            platform["аватар"] = base / platform["аватар"]
    return data


def validate(data):
    """Список человекочитаемых проблем. Пустой список = тема годна."""
    problems = []

    for name in REQUIRED_COLORS:
        if name not in data.get("цвета", {}):
            problems.append(f"цвета: не хватает «{name}»")

    roles = data.get("шрифты", {}).get("роли", {})
    for name in REQUIRED_ROLES:
        if name not in roles:
            problems.append(f"шрифты.роли: не хватает «{name}»")

    steps_map = data.get("ступени", {})
    for name in REQUIRED_STEPS:
        values = steps_map.get(name)
        if not values:
            problems.append(f"ступени: не хватает «{name}»")
        elif len(values) != STEP_COUNT:
            problems.append(f"ступени.{name}: нужно ровно {STEP_COUNT} ступени, "
                            f"а задано {len(values)}")
        elif list(values) != sorted(values, reverse=True):
            problems.append(f"ступени.{name}: должны идти по убыванию")

    for key, path in data.get("шрифты", {}).get("файлы", {}).items():
        if not Path(path).exists():
            problems.append(f"шрифт «{key}» не найден: {path}")
    for key, path in data.get("ассеты", {}).items():
        if not Path(path).exists():
            problems.append(f"ассет «{key}» не найден: {path}")

    for name, platform in data.get("обвязка", {}).items():
        avatar = platform.get("аватар")
        if avatar and not Path(avatar).exists():
            problems.append(f"обвязка.{name}: аватар не найден: {avatar}")
        if not platform.get("подпись"):
            problems.append(f"обвязка.{name}: пустая подпись")

    return problems


def binding(data, platform, layout):
    """Блок обвязки под связку «площадка × лейаут».

    Обвязка — единственное, что зависит от площадки: у IG хэндл одной строкой,
    у LinkedIn имя с должностью в две, и аватарки разные.
    """
    block = data["обвязка"][platform]
    positions = block["позиции"].get(layout) or DEFAULT_POSITIONS.get(layout, {})
    return {
        "аватар": block["аватар"],
        "подпись": list(block["подпись"]),
        "бейдж": positions.get("бейдж", "верх-центр"),
        "подпись_позиция": positions.get("подпись", "низ-центр"),
    }


def steps(data, key):
    """Ступени кегля под роль, от крупной к мелкой."""
    values = data.get("ступени", {}).get(key) or DEFAULT_STEPS.get(key)
    if not values:
        raise KeyError(f"ступени: не задан «{key}» и нет значения по умолчанию")
    return list(values)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("theme_json")
    args = ap.parse_args()
    problems = validate(load(args.theme_json))
    if problems:
        print("\n".join("✗ " + p for p in problems))
        raise SystemExit(1)
    print("✓ тема годна")


if __name__ == "__main__":
    main()
