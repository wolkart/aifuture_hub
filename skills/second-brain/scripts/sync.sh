#!/bin/bash
# Фоновое сохранение второго мозга. Запускает расписание раз в 5 минут: launchd на Маке,
# cron на сервере. Запуск: sync.sh <путь к мозгу> [--chown uid:gid]
#   1. сохраняет все изменения в историю Git (коммит «auto: …»);
#   2. есть GitHub (origin) — забирает чужие правки и отправляет свои.
# Коды: 0 — ок или пропуск, 1 — конфликт, 2 — нет связи / push не удался, 3 — нет пути.
# Конфликт оставляет отметку .git/second-brain-conflict: дальше только локальное сохранение,
# без уведомлений, пока человек не скажет агенту «разбери конфликт».
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

VAULT=""; CHOWN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --chown) CHOWN="$2"; shift 2 ;;
    *) VAULT="$1"; shift ;;
  esac
done

log() { echo "$(date '+%F %T') $*"; }
notify() {
  if [ -n "$SECOND_BRAIN_NOTIFY" ]; then "$SECOND_BRAIN_NOTIFY" "$1" "$2"
  elif [ "$(uname)" = Darwin ]; then osascript -e "display notification \"$2\" with title \"$1\"" >/dev/null 2>&1
  fi
}

[ -n "$VAULT" ] || { echo "нужен путь: sync.sh <путь к мозгу> [--chown uid:gid]"; exit 3; }
cd "$VAULT" 2>/dev/null || { log "пропуск: нет папки $VAULT"; exit 3; }
V=$(pwd -P)
[ -d .git ] || { log "пропуск: $V — не Git-репозиторий"; exit 0; }

# один запуск за раз: расписание и ручной запуск не должны тянуть изменения одновременно
TMP="${TMPDIR:-/tmp}"; TMP="${TMP%/}"
LOCK="$TMP/second-brain-sync-$(printf %s "$V" | cksum | cut -d' ' -f1).lock"
find "$TMP" -maxdepth 1 -name "$(basename "$LOCK")" -mmin +15 -exec rmdir {} \; 2>/dev/null
mkdir "$LOCK" 2>/dev/null || { log "пропуск: синхронизация уже идёт"; exit 0; }
trap 'rmdir "$LOCK" 2>/dev/null; [ -n "$CHOWN" ] && chown -R "$CHOWN" "$V"' EXIT

if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] || [ -f .git/MERGE_HEAD ]; then
  log "пропуск: идёт rebase/merge"; exit 0
fi

# на свежем компьютере имя в Git может быть не задано — тогда подписываемся «Второй мозг»
G=(git)
if [ -z "$(git config user.email)" ]; then
  G=(git -c "user.name=Второй мозг" -c "user.email=second-brain@$(hostname -s 2>/dev/null || echo local)")
fi

git add -A
if ! git diff --cached --quiet; then
  n=$(git diff --cached --name-only | wc -l | tr -d ' ')
  "${G[@]}" commit -q -m "auto: $(date '+%Y-%m-%d %H:%M') · $(hostname -s 2>/dev/null) · файлов: $n"
fi

git remote get-url origin >/dev/null 2>&1 || { log "ок: сохранено на компьютере"; exit 0; }
if [ -f .git/second-brain-conflict ]; then
  log "стоит конфликт: сохранено на компьютере, на GitHub не отправляю — скажи агенту «разбери конфликт»"
  exit 0
fi

BRANCH=$(git symbolic-ref --short HEAD)
git fetch -q origin || { log "нет связи с GitHub — повторю в следующий раз"; exit 2; }
if git rev-parse -q --verify "origin/$BRANCH" >/dev/null; then
  if ! "${G[@]}" rebase -q "origin/$BRANCH" >/dev/null 2>&1; then
    git rebase --abort 2>/dev/null
    : > .git/second-brain-conflict
    log "КОНФЛИКТ — нужна ручная правка"
    notify "Второй мозг: нужна ручная правка" "Изменения с двух устройств пересеклись. Ничего не потеряно — попроси агента разобрать конфликт."
    exit 1
  fi
fi
git push -q origin "$BRANCH" 2>/dev/null && log "ок" || { log "push не удался — повторю в следующий раз"; exit 2; }
