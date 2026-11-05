#!/usr/bin/env bash
# Подключает все скиллы из этой папки через симлинки: в ~/.claude/skills
# (Claude Code, всегда) и в ~/.agents/skills (Kimi Code, если папка есть).
# Для macOS / Linux / Git Bash. Идемпотентно: добавляет только недостающие ссылки.
#
# Запуск:  bash ./skills/install-skills.sh
set -euo pipefail

skills_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Claude Code ищет скиллы в ~/.claude/skills; Kimi Code — в ~/.agents/skills.
# Подключаем в обе, если папка назначения есть или это ~/.claude/skills (основная).
global_dirs=("$HOME/.claude/skills" "$HOME/.agents/skills")

for global_dir in "${global_dirs[@]}"; do
  if [ "$global_dir" != "$HOME/.claude/skills" ] && [ ! -d "$global_dir" ]; then
    echo "~/.agents/skills нет — Kimi Code не установлен, пропускаю вторую папку"
    continue
  fi
  mkdir -p "$global_dir"
  for dir in "$skills_dir"/*/; do
    [ -f "${dir}SKILL.md" ] || continue
    name="$(basename "$dir")"
    link="$global_dir/$name"
    if [ -e "$link" ] || [ -L "$link" ]; then
      echo "= уже подключён: $name -> $global_dir"
      continue
    fi
    ln -s "${dir%/}" "$link"
    echo "+ подключён:     $name -> $global_dir"
  done
done

echo ""
echo "Готово. Скиллы доступны во всех проектах. Если переместишь репозиторий —"
echo "ссылки станут битыми: удали их из ~/.claude/skills (и ~/.agents/skills) и запусти скрипт заново."
