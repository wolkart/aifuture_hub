#!/usr/bin/env python3
"""Арифметика разведки: длительность, тип ролика, медианы, кратности. Только stdlib."""
import datetime
import re
import statistics

SHORT_MAX_SEC = 180

_DUR = re.compile(
    r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
)


def parse_duration(iso):
    """ISO 8601 из contentDetails.duration → секунды. Мусор → 0."""
    if not iso:
        return 0
    m = _DUR.fullmatch(iso.strip())
    if not m:
        return 0
    days, hours, mins, secs = (int(g) if g else 0 for g in m.groups())
    return days * 86400 + hours * 3600 + mins * 60 + secs


def classify_kind(duration_sec):
    """Граница эвристическая: YouTube поднимал лимит Shorts до 3 минут."""
    return "short" if duration_sec <= SHORT_MAX_SEC else "long"


def medians_by_kind(records):
    """Медиана просмотров ОТДЕЛЬНО по каждому типу — иначе шорты топят длинные."""
    out = {}
    for kind in ("short", "long"):
        views = [r["views"] for r in records if r.get("kind") == kind
                 and r.get("views") is not None]
        out[kind] = statistics.median(views) if views else None
    return out


def median_multiple(views, median):
    """Во сколько раз ролик обогнал медиану своего типа."""
    if not median:
        return None
    return round(views / median, 2)


def views_per_day(views, date_iso, today=None):
    """Скорость набора. Минимум 1 день, чтобы вчерашний ролик не улетал в бесконечность."""
    today = today or datetime.date.today()
    published = datetime.date.fromisoformat(date_iso[:10])
    days = max((today - published).days, 1)
    return round(views / days, 2)


def engagement_rate(likes, comments, views):
    if not views:
        return None
    return round(((likes or 0) + (comments or 0)) / views, 4)


def enrich_records(records, today=None):
    """Дописывает производные поля в записи (на месте) и возвращает список."""
    medians = medians_by_kind(records)
    for r in records:
        r["median_multiple"] = median_multiple(
            r.get("views") or 0, medians.get(r.get("kind")))
        r["views_per_day"] = views_per_day(
            r.get("views") or 0, r["date"], today)
        r["engagement_rate"] = engagement_rate(
            r.get("likes"), r.get("comments"), r.get("views") or 0)
    return records
