#!/usr/bin/env python3
"""Рендер выгрузки в волт: index.md + карточки + CSV + Obsidian Base.

Контракт повторяет instagram-analytics. Идемпотентность по id;
ручные заметки и секции enrich при перезаписи сохраняются.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

BASE_NAME = "_Разведка YouTube.base"

COLUMNS = ["id", "title", "channel", "url", "kind", "date", "duration_sec",
           "views", "likes", "comments", "median_multiple", "views_per_day",
           "engagement_rate", "description", "tags", "thumbnail_url",
           "tier2_status", "intro_transcript", "top_comments", "notes"]

KEEP_SECTIONS = ("## Текст на превью", "## Вступление (дословно)",
                 "## Разбор вступления", "## Главы", "## Комментарии",
                 "## Заметки")


def short_title(title, limit=60):
    """Читаемый ярлык для навигации. Режем по границе слова."""
    clean = (title or "").replace("|", "／").replace("[", "(").replace(
        "]", ")").strip()
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(" ,.—-")


def _yaml_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "[" + ", ".join(str(v) for v in value) + "]"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def card_markdown(record, channel):
    label = short_title(record["title"])
    head = ["---", 'aliases: ["%s"]' % label]
    for field in ("id", "title", "url", "kind", "date", "duration_sec",
                  "views", "likes", "comments", "median_multiple",
                  "views_per_day", "engagement_rate", "thumbnail_url"):
        head.append("%s: %s" % (field, _yaml_value(record.get(field))))
    head.append("channel: %s" % channel.get("handle", ""))
    head.append("tags_video: %s" % _yaml_value(record.get("tags", [])))
    head.append("tier2_status: %s" % record.get("tier2_status", "skeleton"))
    head.append("---")

    body = [
        "",
        "# " + label,
        "",
        "*[[%s]] · %s · %s · %s просмотров · кратность %s*" % (
            channel.get("handle", ""), record["kind"], record["date"],
            record["views"], record.get("median_multiple")),
        "",
        "## Тайтл",
        record["title"],
        "",
        "## Описание",
        record.get("description", "") or "",
        "",
        "## Текст на превью",
        record.get("thumbnail_text") or "(пусто — прогони режим thumbs)",
        "",
        "## Вступление (дословно)",
        "(пусто до enrich)",
        "",
        "## Разбор вступления",
        "- **Хук (0–3 сек):** (пусто до enrich)",
        "- **Обещание:** (пусто до enrich)",
        "- **Первое доказательство:** (пусто до enrich)",
        "",
        "## Главы",
        "(пусто до enrich)",
        "",
        "## Комментарии",
        "(пусто до enrich)",
        "",
        "## Заметки",
        "",
    ]
    return "\n".join(head + body)


def _section_body(text, header):
    pattern = re.compile(
        "^" + re.escape(header) + r"\n(.*?)(?=^## |\Z)", re.S | re.M)
    m = pattern.search(text)
    return m.group(1) if m else ""


def _replace_section(text, header, body):
    pattern = re.compile(
        "^(" + re.escape(header) + r"\n)(.*?)(?=^## |\Z)", re.S | re.M)
    return pattern.sub(lambda m: m.group(1) + body, text)


def _merge_preserved(new_text, old_text):
    """Сохраняет содержимое секций, которые наполняет enrich или человек."""
    if not old_text:
        return new_text
    for section in KEEP_SECTIONS:
        old_block = _section_body(old_text, section)
        if old_block and old_block.strip() and "(пусто до enrich)" not in old_block:
            new_text = _replace_section(new_text, section, old_block)
    return new_text


def _rows_table(rows):
    out = ["| # | Тема | кратность | просмотры | лайки | комменты | дата | "
           "длит. | tier2 |",
           "|---|------|-----------|-----------|-------|----------|------|"
           "-------|-------|"]
    for i, v in enumerate(rows, 1):
        out.append("| %d | [[cards/%s\\|%s]] | %s | %d | %s | %s | %s | %d с | %s |"
                   % (i, v["id"], short_title(v["title"]),
                      v.get("median_multiple"), v["views"],
                      v.get("likes") if v.get("likes") is not None else "—",
                      v.get("comments") if v.get("comments") is not None
                      else "—",
                      v["date"], v["duration_sec"],
                      v.get("tier2_status", "skeleton")))
    return out


def index_markdown(data):
    ch = data["channel"]
    out = [
        "# Разведка: @%s — scout %s" % (ch.get("handle", ""),
                                        data.get("collected_at", "")),
        "",
        "Источник: YouTube Data API v3 · подписчиков: %s · роликов: %d"
        % (ch.get("subscribers") if ch.get("subscribers") is not None
           else "скрыто", len(data["videos"])),
        "",
        "Ранжировано по **кратности к медиане своего типа** "
        "(просмотры / медиана Shorts или длинных отдельно). "
        "Клик по теме → карточка.",
        "",
    ]
    for label, kind in (("Длинные", "long"), ("Shorts", "short")):
        rows = [v for v in data["videos"] if v["kind"] == kind]
        if not rows:
            continue
        rows.sort(key=lambda v: v.get("median_multiple") or 0, reverse=True)
        out += ["## " + label, ""] + _rows_table(rows) + [""]
    return "\n".join(out)


def write_base(root):
    path = Path(root) / BASE_NAME
    path.write_text("""filters:
  and:
    - file.hasProperty("median_multiple")
    - file.folder.contains("cards")
views:
  - type: table
    name: Все по кратности
    order: [file.name, title, channel, kind, median_multiple, views, tier2_status]
    sort:
      - property: median_multiple
        direction: DESC
  - type: table
    name: По каналам
    order: [file.name, title, channel, median_multiple, views, date]
    sort:
      - property: channel
        direction: ASC
      - property: median_multiple
        direction: DESC
""", encoding="utf-8")
    return str(path)


def write_all(data, out_dir):
    ch = data["channel"]
    root = Path(out_dir)
    channel_dir = root / (ch.get("handle") or ch.get("channel_id"))
    cards_dir = channel_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    for v in data["videos"]:
        v.setdefault("tier2_status", "skeleton")
        card = cards_dir / (v["id"] + ".md")
        old = card.read_text(encoding="utf-8") if card.exists() else ""
        card.write_text(_merge_preserved(card_markdown(v, ch), old),
                        encoding="utf-8")

    (channel_dir / "index.md").write_text(index_markdown(data),
                                          encoding="utf-8")

    with (channel_dir / "export.csv").open("w", newline="",
                                           encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS,
                                extrasaction="ignore")
        writer.writeheader()
        for v in data["videos"]:
            row = dict(v)
            row["channel"] = ch.get("handle", "")
            row["tags"] = ";".join(v.get("tags", []))
            writer.writerow(row)

    return {"channel_dir": str(channel_dir),
            "index": str(channel_dir / "index.md"),
            "csv": str(channel_dir / "export.csv"),
            "base": write_base(root)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="выгрузка канала в волт")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args(argv)
    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    print(json.dumps(write_all(data, args.out_dir), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
