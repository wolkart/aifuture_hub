# ASR (Tier-2) — транскрибация рилса

Конфигурируемо через `ASR_PROVIDER` (.env): `openai` | `local` | `apify` | `none`. **Грациозная деградация:** `none` или ошибка → транскрипт пуст, разбор делается по подписи; Tier-1-данные не трогаются.

## Шаг 0 — извлечь аудио из видео
```bash
yt-dlp -x --audio-format mp3 "<video_url>" -o "audio-<id>.mp3"
# либо, если video_url прямой:
# curl -L "<video_url>" -o "v-<id>.mp4" && ffmpeg -i "v-<id>.mp4" -vn -acodec libmp3lame "audio-<id>.mp3"
```

## openai (Whisper API) — нужен `OPENAI_API_KEY`
```bash
curl --silent https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F file="@audio-<id>.mp3" -F model="whisper-1"
# ответ: {"text":"..."} → transcript
```

## local (whisper/faster-whisper установлен)
```bash
whisper "audio-<id>.mp3" --model small --output_format txt
# текст из audio-<id>.txt → transcript
```

## apify (ASR-актор) — нужен `APIFY_ASR_ACTOR`
Вызов как в references/apify.md (run-sync), вход — ссылка/файл аудио; из ответа взять текстовое поле → transcript.

## none / ошибка
Транскрипт = пусто. В карточке пометь: «транскрипт недоступен (ASR не настроен)». Переходи к разбору по подписи (см. scenario-breakdown.md).
