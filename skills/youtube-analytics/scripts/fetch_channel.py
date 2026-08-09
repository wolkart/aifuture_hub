#!/usr/bin/env python3
"""scout: канал → нормализованный .channel.json. Только stdlib.

Квота: channels 1 + playlistItems 1/страница + videos 1/пачка.
Канал на 300 роликов ≈ 14 юнитов из 10 000.
"""
import argparse
import datetime
import json
import os
import sys
from pathlib import Path

import metrics
import yt_api

PAGE = 50


def read_env(path):
    """Читает .env БЕЗ source: zsh ломается на значениях с пробелами."""
    env = {}
    path = Path(path)
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        env[name.strip()] = value.strip().strip('"').strip("'")
    return env


def require_key(env):
    key = env.get("YOUTUBE_API_KEY") or os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit(
            "нет YOUTUBE_API_KEY. Заведи ключ в Google Cloud "
            "(включи YouTube Data API v3) и положи в "
            "skills/youtube-analytics/.env")
    return key


def collect(handle, key, limit=300, getter=None, today=None):
    """Собирает канал целиком. getter подменяется в тестах."""
    getter = getter or (lambda ep, p, k: yt_api.api_get(ep, p, k))
    units = 0

    handle_clean = handle.lstrip("@")
    channel = yt_api.resolve_channel(
        getter("channels",
               {"part": "snippet,statistics,contentDetails",
                "forHandle": "@" + handle_clean}, key))
    units += 1

    video_ids = []
    token = None
    while len(video_ids) < limit:
        params = {"part": "contentDetails",
                  "playlistId": channel["uploads_playlist"],
                  "maxResults": PAGE}
        if token:
            params["pageToken"] = token
        page = getter("playlistItems", params, key)
        units += 1
        ids, token = yt_api.parse_playlist_page(page)
        video_ids.extend(ids)
        if not token:
            break
    video_ids = video_ids[:limit]

    videos = []
    for batch in yt_api.chunked(video_ids, PAGE):
        page = getter("videos",
                      {"part": "snippet,statistics,contentDetails",
                       "id": ",".join(batch)}, key)
        units += 1
        videos.extend(yt_api.parse_videos(page))

    metrics.enrich_records(videos, today)
    videos.sort(key=lambda v: (v.get("median_multiple") or 0), reverse=True)

    return {
        "channel": channel,
        "videos": videos,
        "quota_units": units,
        "requested_limit": limit,
        "collected_at": (today or datetime.date.today()).isoformat(),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="scout канала YouTube")
    ap.add_argument("handle", help="@handle канала")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--out", required=True, help="куда писать .channel.json")
    ap.add_argument("--env", default=str(
        Path(__file__).parent.parent / ".env"))
    args = ap.parse_args(argv)

    key = require_key(read_env(args.env))
    result = collect(args.handle, key, args.limit)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(json.dumps({
        "channel": result["channel"]["title"],
        "videos": len(result["videos"]),
        "quota_units": result["quota_units"],
        "out": str(out),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
