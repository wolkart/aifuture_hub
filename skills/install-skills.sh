#!/usr/bin/env bash
# Подключает все скиллы из этой папки в ~/.claude/skills через симлинки.
# Для macOS / Linux / Git Bash. Идемпотентно: добавляет только недостающие ссылки.
#
# Запуск:  bash ./skills/install-skills.sh
set -euo pipefail

skills_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
global_dir="$HOME/.claude/skills"
mkdir -p "$global_dir"

for dir in "$skills_dir"/*/; do
  [ -f "${dir}SKILL.md" ] || continue
  name="$(basename "$dir")"
  link="$global_dir/$name"
  if [ -e "$link" ] || [ -L "$link" ]; then
    echo "= уже подключён: $name"
    continue
  fi
  ln -s "${dir%/}" "$link"
  echo "+ подключён:     $name"
done

echo ""
echo "Готово. Скиллы доступны во всех проектах. Если переместишь репозиторий —"
echo "ссылки станут битыми: удали их из ~/.claude/skills и запусти скрипт заново."
