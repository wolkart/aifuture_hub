#!/bin/bash
# Ставит фоновое сохранение второго мозга на Маке: копия sync.sh в ~/.local/bin и задача launchd
# раз в 5 минут. Повторный запуск обновляет скрипт и задачу.
# Запуск: bash install-sync.sh <путь к мозгу> [--label local.second-brain.sync] [--no-load]
set -euo pipefail
VAULT=""; LABEL="local.second-brain.sync"; LOAD=1
while [ $# -gt 0 ]; do
  case "$1" in
    --label) LABEL="$2"; shift 2 ;;
    --no-load) LOAD=0; shift ;;
    *) VAULT="$1"; shift ;;
  esac
done
[ "$(uname)" = Darwin ] || { echo "Только для Мака. Windows — scripts/windows-task.ps1, сервер — cron (references/server.md)."; exit 1; }
[ -n "$VAULT" ] && [ -d "$VAULT" ] || { echo "нужен путь к папке мозга: install-sync.sh <путь>"; exit 1; }
VAULT=$(cd "$VAULT" && pwd -P)
HERE=$(cd "$(dirname "$0")" && pwd -P)

BIN="$HOME/.local/bin/second-brain-sync.sh"
LOG="$HOME/Library/Logs/second-brain-sync.log"
if [ "$LABEL" != "local.second-brain.sync" ]; then   # своя метка (проба) — свои скрипт и лог, настоящие не трогаем
  BIN="$HOME/.local/bin/$LABEL.sh"; LOG="$HOME/Library/Logs/$LABEL.log"
fi
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$(dirname "$BIN")" "$(dirname "$PLIST")" "$(dirname "$LOG")"
cp "$HERE/sync.sh" "$BIN"
chmod +x "$BIN"

esc() { printf %s "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$(esc "$LABEL")</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$(esc "$BIN")</string><string>$(esc "$VAULT")</string></array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$(esc "$LOG")</string>
  <key>StandardErrorPath</key><string>$(esc "$LOG")</string>
</dict>
</plist>
PLIST

if [ "$LOAD" = 1 ]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
fi
echo "Готово: $LABEL каждые 5 минут сохраняет $VAULT. Лог — $LOG"
