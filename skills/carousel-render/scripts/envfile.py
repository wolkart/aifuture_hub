#!/usr/bin/env python3
"""Подхват `.env` рядом со скиллом. Только stdlib.

README обещает: заполнил `.env` — работает. Но сами скрипты читают
os.environ, а файл никто не разбирал, поэтому запуск требовал руками
экспортировать переменные в шелл. Этот модуль закрывает разрыв.

Уже заданные переменные окружения имеют приоритет: разовый прогон с другой
темой делается через `THEME_PATH=… python3 …`, и файл его не перебьёт.
"""
import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def parse(text):
    """Строки `КЛЮЧ=значение` → словарь. Комментарии и пустые строки мимо."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            out[key] = value
    return out


def load(path=None):
    """Кладёт значения из `.env` в os.environ, не перебивая уже заданные.

    Возвращает то, что реально применилось — пустой словарь, если файла нет
    или всё уже пришло из окружения.
    """
    path = Path(path) if path else SKILL_ROOT / ".env"
    if not path.exists():
        return {}
    applied = {}
    for key, value in parse(path.read_text(encoding="utf-8")).items():
        if value and not os.environ.get(key):
            os.environ[key] = value
            applied[key] = value
    return applied
