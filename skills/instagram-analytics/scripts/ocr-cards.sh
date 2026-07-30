#!/usr/bin/env bash
# ocr-cards.sh — текст с карточек карусели: ocr-cards.sh slide-*.jpg
#
# Компилирует ocr-cards.swift один раз (~7 с) и кеширует бинарник рядом,
# в .build/. Дальше каждый прогон — ~0.3 с на карточку. Пересобирает сам,
# если исходник новее бинарника.
#
# Имена переменных латиницей: bash не принимает кириллицу в именах, хотя
# в комментариях и строках она живёт нормально.
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
src="$dir/ocr-cards.swift"
cache="$dir/.build"
bin="$cache/ocr-cards"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "ocr-cards: нужен macOS — Vision есть только там." >&2
  exit 1
fi
if ! command -v swiftc >/dev/null 2>&1; then
  echo "ocr-cards: нет swiftc. Поставь Command Line Tools: xcode-select --install" >&2
  exit 1
fi
if [[ $# -eq 0 ]]; then
  echo "Использование: ocr-cards.sh <картинка> [...]  (слайды по возрастанию номера)" >&2
  exit 2
fi

mkdir -p "$cache"
if [[ ! -x "$bin" || "$src" -nt "$bin" ]]; then
  echo "ocr-cards: собираю бинарник (один раз)…" >&2
  swiftc -O -o "$bin" "$src"
fi

exec "$bin" "$@"
