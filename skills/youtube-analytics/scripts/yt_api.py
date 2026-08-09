#!/usr/bin/env python3
"""Клиент YouTube Data API v3. Только stdlib.

Парсеры — чистые функции от готового JSON, сеть живёт только в api_get:
так всё тестируется без единого сетевого вызова.

search.list НЕ используется: 100 юнитов из 10 000 и неполная выборка.
Список роликов берётся через плейлист загрузок канала.
"""
import json
import re
import urllib.parse
import urllib.request

import metrics

BASE = "https://www.googleapis.com/youtube/v3"
TIMEOUT = 30
THUMB_ORDER = ("maxres", "standard", "high", "medium", "default")


def safe_url(url):
    """URL без ключа — для логов и сообщений об ошибках."""
    return re.sub(r"key=[^&]+", "key=***", url)


def api_get(endpoint, params, key, opener=None):
    """GET к Data API. opener подменяется в тестах."""
    opener = opener or urllib.request.urlopen
    query = dict(params)
    query["key"] = key
    url = BASE + "/" + endpoint + "?" + urllib.parse.urlencode(query)
    try:
        with opener(url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "запрос к " + safe_url(url) + " не прошёл: " + str(exc))


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _int_or_none(value):
    return int(value) if value not in (None, "") else None


def resolve_channel(payload):
    items = payload.get("items") or []
    if not items:
        raise LookupError("канал не найден: проверь @handle")
    it = items[0]
    snippet = it.get("snippet", {})
    return {
        "channel_id": it.get("id", ""),
        "title": snippet.get("title", ""),
        "handle": (snippet.get("customUrl", "") or "").lstrip("@"),
        "subscribers": _int_or_none(
            it.get("statistics", {}).get("subscriberCount")),
        "uploads_playlist": it.get("contentDetails", {})
                              .get("relatedPlaylists", {}).get("uploads", ""),
    }


def parse_playlist_page(payload):
    ids = [i["contentDetails"]["videoId"]
           for i in payload.get("items", [])
           if i.get("contentDetails", {}).get("videoId")]
    return ids, payload.get("nextPageToken")


def best_thumbnail(thumbnails):
    for name in THUMB_ORDER:
        url = (thumbnails or {}).get(name, {}).get("url")
        if url:
            return url
    return ""


def parse_videos(payload):
    rows = []
    for it in payload.get("items", []):
        snippet = it.get("snippet", {})
        stats = it.get("statistics", {})
        duration_sec = metrics.parse_duration(
            it.get("contentDetails", {}).get("duration"))
        rows.append({
            "id": it.get("id", ""),
            "title": snippet.get("title", ""),
            "url": "https://www.youtube.com/watch?v=" + it.get("id", ""),
            "date": (snippet.get("publishedAt", "") or "")[:10],
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []) or [],
            "thumbnail_url": best_thumbnail(snippet.get("thumbnails")),
            "duration_sec": duration_sec,
            "kind": metrics.classify_kind(duration_sec),
            "views": int(stats.get("viewCount", 0) or 0),
            "likes": _int_or_none(stats.get("likeCount")),
            "comments": _int_or_none(stats.get("commentCount")),
        })
    return rows


def parse_comments(payload):
    out = []
    for it in payload.get("items", []):
        top = (it.get("snippet", {})
                 .get("topLevelComment", {}).get("snippet", {}))
        out.append({
            "text": top.get("textOriginal", ""),
            "likes": int(top.get("likeCount", 0) or 0),
            "author": top.get("authorDisplayName", ""),
        })
    out.sort(key=lambda c: c["likes"], reverse=True)
    return out
