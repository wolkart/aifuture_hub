#!/usr/bin/env python3
"""patterns: закономерности канала по уже собранным метрикам. Только stdlib.

Считает офлайн по .channel.json — к API не обращается, квоту не тратит.
Группа меньше MIN_GROUP роликов помечается ненадёжной: один удачный ролик
не должен превращаться в «закономерность».
"""
import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

MIN_GROUP = 5
TOP_N = 15

TITLE_LEN_EDGES = [(0, 40, "≤40"), (41, 60, "41–60"),
                   (61, 80, "61–80"), (81, 9999, "81+")]
DURATION_EDGES = [(0, 180, "Shorts ≤3мин"), (181, 480, "3–8 мин"),
                  (481, 900, "8–15 мин"), (901, 1800, "15–30 мин"),
                  (1801, 999999, "30+ мин")]
DESC_LEN_EDGES = [(0, 300, "≤300"), (301, 800, "301–800"),
                  (801, 2000, "801–2000"), (2001, 999999, "2000+")]

_TIMECODE_LINE = re.compile(r"^\s*\d{1,2}:\d{2}(?::\d{2})?\s+\S", re.M)
_YEAR_TAG = re.compile(r"\((?:19|20)\d{2}\)")
_CAPS_WORD = re.compile(r"\b[A-ZА-ЯЁ]{4,}\b")


def has_timecodes(description):
    """Блок глав = минимум две строки, начинающиеся с таймкода."""
    return len(_TIMECODE_LINE.findall(description or "")) >= 2


def title_features(title):
    title = title or ""
    return {
        "has_digit": any(ch.isdigit() for ch in title),
        "has_year_tag": bool(_YEAR_TAG.search(title)),
        "has_brackets": ("(" in title) or ("[" in title),
        "has_caps": bool(_CAPS_WORD.search(title)),
        "has_question": "?" in title,
    }


def bucket(value, edges):
    for low, high, label in edges:
        if low <= value <= high:
            return label
    return edges[-1][2]


def _median_mult(records):
    vals = [r["median_multiple"] for r in records
            if r.get("median_multiple") is not None]
    return round(statistics.median(vals), 2) if vals else None


def slice_stats(records, key_fn):
    groups = defaultdict(list)
    for r in records:
        groups[key_fn(r)].append(r)
    return {
        label: {
            "n": len(rows),
            "median_multiple": _median_mult(rows),
            "reliable": len(rows) >= MIN_GROUP,
        }
        for label, rows in groups.items()
    }


def by_month(records):
    out = defaultdict(lambda: defaultdict(list))
    for r in records:
        out[r["date"][:7]][r["kind"]].append(r["views"])
    return {
        month: {
            kind: {"n": len(views),
                   "median_views": statistics.median(views),
                   "reliable": len(views) >= MIN_GROUP}
            for kind, views in kinds.items()
        }
        for month, kinds in out.items()
    }


def _composition_slices(videos):
    out = {}
    for flag in ("has_digit", "has_year_tag", "has_brackets",
                 "has_caps", "has_question"):
        out[flag] = slice_stats(
            videos, lambda r, f=flag: "да" if title_features(r["title"])[f]
            else "нет")
    return out


def build_report(data):
    videos = data["videos"]
    ranked = [v for v in videos if v.get("median_multiple") is not None]
    ranked.sort(key=lambda v: v["median_multiple"], reverse=True)

    def extreme(rows):
        return [{"title": v["title"], "kind": v["kind"],
                 "views": v["views"],
                 "median_multiple": v["median_multiple"],
                 "url": v.get("url", "")} for v in rows]

    return {
        "total": len(videos),
        "by_kind": {k: sum(1 for v in videos if v["kind"] == k)
                    for k in ("short", "long")},
        "by_month": by_month(videos),
        "title_length": slice_stats(
            videos, lambda r: bucket(len(r["title"]), TITLE_LEN_EDGES)),
        "title_composition": _composition_slices(videos),
        "duration": slice_stats(
            videos, lambda r: bucket(r["duration_sec"], DURATION_EDGES)),
        "description": {
            "length": slice_stats(
                videos,
                lambda r: bucket(len(r.get("description") or ""),
                                 DESC_LEN_EDGES)),
            "timecodes": slice_stats(
                videos,
                lambda r: "есть главы" if has_timecodes(r.get("description"))
                else "нет глав"),
        },
        "extremes": {"top": extreme(ranked[:TOP_N]),
                     "bottom": extreme(ranked[-TOP_N:][::-1])},
        "rhythm": slice_stats(videos, lambda r: r["date"][:7]),
    }


def _table(title, stats):
    lines = ["### " + title, "",
             "| группа | роликов | медианная кратность | надёжно |",
             "|---|---|---|---|"]
    for label in sorted(stats, key=lambda k: str(k)):
        s = stats[label]
        lines.append("| %s | %d | %s | %s |" % (
            label, s["n"],
            "—" if s["median_multiple"] is None else s["median_multiple"],
            "да" if s["reliable"] else "нет (<%d)" % MIN_GROUP))
    lines.append("")
    return lines


def _thumbs_section(thumbs):
    """Раздел 8 — только если режим thumbs отработал."""
    if not thumbs:
        return []
    out = ["## 8. Текст на превью", ""]
    if thumbs.get("skipped"):
        return out + [thumbs["skipped"], ""]
    out += ["Распознано у %d превью из %d. На превью работает та же ось, что "
            "в тайтле: цена, имя инструмента, конкретика."
            % (thumbs.get("covered", 0), thumbs.get("total", 0)),
            "",
            "| признак на превью | с признаком | без | роликов | надёжно |",
            "|---|---|---|---|---|"]
    for name in sorted(thumbs.get("slices", {})):
        s = thumbs["slices"][name]
        out.append("| %s | %s | %s | %d | %s |" % (
            name,
            "—" if s["median_multiple"] is None else s["median_multiple"],
            "—" if s["median_without"] is None else s["median_without"],
            s["n"], "да" if s["reliable"] else "нет (<%d)" % MIN_GROUP))
    out.append("")
    return out


def render_markdown(report, channel, thumbs=None):
    out = [
        "# Разбор — тайтлы и паттерны: %s" % channel.get("title", ""),
        "",
        "Канал: `@%s` · подписчиков: %s · роликов в выборке: %d "
        "(Shorts %d / длинных %d)" % (
            channel.get("handle", ""),
            channel.get("subscribers") if channel.get("subscribers")
            is not None else "скрыто",
            report["total"], report["by_kind"]["short"],
            report["by_kind"]["long"]),
        "",
        "Кратность = просмотры / медиана СВОЕГО типа. Группы меньше %d "
        "роликов помечены ненадёжными — на них выводы не строим." % MIN_GROUP,
        "",
    ]

    out += ["## 1. Медиана просмотров по месяцам", "",
            "| месяц | тип | роликов | медиана просмотров | надёжно |",
            "|---|---|---|---|---|"]
    for month in sorted(report["by_month"], reverse=True):
        for kind, s in sorted(report["by_month"][month].items()):
            out.append("| %s | %s | %d | %d | %s |" % (
                month, kind, s["n"], s["median_views"],
                "да" if s["reliable"] else "нет"))
    out.append("")

    out += ["## 2. Длина тайтла", ""] + _table("Символов в тайтле",
                                               report["title_length"])
    out += ["## 3. Состав тайтла", ""]
    names = {"has_digit": "Цифра в тайтле",
             "has_year_tag": "Тег свежести (год)",
             "has_brackets": "Скобки",
             "has_caps": "CAPS-слово",
             "has_question": "Вопрос"}
    for flag, stats in report["title_composition"].items():
        out += _table(names[flag], stats)

    out += ["## 4. Длительность", ""] + _table("Длительность",
                                               report["duration"])
    out += ["## 5. Описание", ""]
    out += _table("Длина описания", report["description"]["length"])
    out += _table("Блок глав в описании", report["description"]["timecodes"])

    out += ["## 6. Верх и низ по кратности", "",
            "Здесь смотрим глазами: механику тайтла посчитать нельзя, "
            "её видно только на контрасте верха и низа.", ""]
    for label, rows in (("Топ", report["extremes"]["top"]),
                        ("Дно", report["extremes"]["bottom"])):
        out += ["### %s-%d" % (label, TOP_N), "",
                "| кратность | тип | просмотры | тайтл |", "|---|---|---|---|"]
        for r in rows:
            out.append("| %s | %s | %d | %s |" % (
                r["median_multiple"], r["kind"], r["views"],
                r["title"].replace("|", "\\|")))
        out.append("")

    out += ["## 7. Ритм публикаций", ""] + _table("Роликов в месяц",
                                                  report["rhythm"])
    out += _thumbs_section(thumbs)
    out += ["## Что забираем себе", "",
            "_Заполняется руками после чтения срезов выше: "
            "механика тайтлов из топа, что НЕ повторять из дна, "
            "рабочая длительность и ритм._", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="patterns по .channel.json")
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    data = json.loads(Path(args.src).read_text(encoding="utf-8"))
    report = build_report(data)
    # режим thumbs отработал раньше — подхватываем его срез, если он рядом
    thumbs_path = Path(args.src).parent / ".thumbs.json"
    thumbs = (json.loads(thumbs_path.read_text(encoding="utf-8"))
              if thumbs_path.exists() else None)
    Path(args.out).write_text(
        render_markdown(report, data["channel"], thumbs), encoding="utf-8")
    print(json.dumps({"videos": report["total"], "out": args.out},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
