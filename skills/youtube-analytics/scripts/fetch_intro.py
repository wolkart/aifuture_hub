#!/usr/bin/env python3
"""enrich: вступление ролика дословно + главы. Через yt-dlp, только stdlib.

Видео НИКОГДА не скачивается: только --skip-download.
Субтитров нет → отдаём пустое вступление и честный флаг, а не падаем.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TIMECODE = re.compile(r"^(\d\d):(\d\d):(\d\d)\.\d+\s+-->")
TAGS = re.compile(r"<[^>]+>")
DEFAULT_WINDOW = 60


def _run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True,
                          check=False, **kwargs).stdout


def parse_vtt(text):
    """VTT → реплики без дублей.

    Авто-субтитры YouTube «катятся»: каждая карточка повторяет предыдущую
    строку. Дедупим по тексту, сохраняя первое появление.
    """
    cues = []
    seen = set()
    current = None
    for line in (text or "").splitlines():
        m = TIMECODE.match(line.strip())
        if m:
            h, mm, ss = (int(g) for g in m.groups())
            current = h * 3600 + mm * 60 + ss
            continue
        clean = TAGS.sub("", line).strip()
        if current is None or not clean or clean.startswith("WEBVTT"):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        cues.append({"sec": current,
                     "t": "%02d:%02d" % (current // 60, current % 60),
                     "text": clean})
    return cues


def intro_lines(cues, seconds=DEFAULT_WINDOW):
    return [c for c in cues if c["sec"] <= seconds]


def format_intro(cues):
    return "\n".join("%s %s" % (c["t"], c["text"]) for c in cues)


def pick_sub_lang(meta):
    """Одна дорожка — оригинальная, а не перевод.

    У русского ролика YouTube генерирует en-субтитры НА ЛЕТУ и на запрос
    отвечает 429; yt-dlp при этом падает целиком и не сохраняет даже ту
    дорожку, что была доступна. Поэтому просим ровно один язык — тот,
    на котором ролик записан.
    """
    meta = meta or {}
    manual = meta.get("subtitles") or {}
    auto = meta.get("automatic_captions") or {}
    lang = meta.get("language")

    if lang and lang in manual:
        return lang
    for key in auto:
        if key.endswith("-orig"):
            return key
    if lang:
        return lang
    return "en"


def chapters_from_json(payload):
    chapters = (payload or {}).get("chapters") or []
    return [{"start_sec": int(c.get("start_time") or 0),
             "title": c.get("title", "")} for c in chapters]


def fetch(video_id, runner=None, workdir=None, seconds=DEFAULT_WINDOW):
    runner = runner or _run
    url = "https://www.youtube.com/watch?v=" + video_id

    meta_raw = runner(["yt-dlp", "-J", "--skip-download", url])
    try:
        meta = json.loads(meta_raw) if meta_raw else {}
    except ValueError:
        meta = {}

    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp())
    tmp.mkdir(parents=True, exist_ok=True)
    runner(["yt-dlp", "--skip-download", "--write-auto-subs",
            "--write-subs", "--sub-langs", pick_sub_lang(meta),
            "--sub-format", "vtt",
            "-o", str(tmp / "%(id)s.%(ext)s"), url])

    vtt_files = sorted(tmp.glob("*.vtt"))
    if not vtt_files:
        return {"video_id": video_id, "title": meta.get("title", ""),
                "subtitles_available": False, "intro": "",
                "chapters": chapters_from_json(meta)}

    cues = parse_vtt(vtt_files[0].read_text(encoding="utf-8"))
    return {
        "video_id": video_id,
        "title": meta.get("title", ""),
        "subtitles_available": bool(cues),
        "intro": format_intro(intro_lines(cues, seconds)),
        "chapters": chapters_from_json(meta),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="вступление ролика + главы")
    ap.add_argument("video_id")
    ap.add_argument("--seconds", type=int, default=DEFAULT_WINDOW)
    args = ap.parse_args(argv)
    print(json.dumps(fetch(args.video_id, seconds=args.seconds),
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
