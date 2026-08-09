import json

import fetch_intro

VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.080 --> 00:00:02.560 align:start position:0%
Anthropic just dropped Claude Opus 5 and

00:00:02.560 --> 00:00:05.120 align:start position:0%
Anthropic just dropped Claude Opus 5 and
it is by far probably the best Frontier

00:00:05.120 --> 00:00:07.200 align:start position:0%
it is by far probably the best Frontier
large language model currently available

00:01:30.000 --> 00:01:32.000
this line is past the intro window
"""


def test_parse_vtt_dedupes_rolling_captions():
    cues = fetch_intro.parse_vtt(VTT)
    texts = [c["text"] for c in cues]
    assert texts == [
        "Anthropic just dropped Claude Opus 5 and",
        "it is by far probably the best Frontier",
        "large language model currently available",
        "this line is past the intro window",
    ]


def test_parse_vtt_keeps_seconds():
    cues = fetch_intro.parse_vtt(VTT)
    assert cues[0]["sec"] == 0
    assert cues[3]["sec"] == 90


def test_parse_vtt_strips_inline_tags():
    text = ("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n"
            "<c.colorE5E5E5>привет</c> мир\n")
    assert fetch_intro.parse_vtt(text)[0]["text"] == "привет мир"


def test_parse_vtt_empty_input():
    assert fetch_intro.parse_vtt("") == []


def test_intro_lines_cuts_at_window():
    cues = fetch_intro.parse_vtt(VTT)
    intro = fetch_intro.intro_lines(cues, seconds=60)
    assert len(intro) == 3
    assert all(c["sec"] <= 60 for c in intro)


def test_format_intro_has_timecodes():
    cues = fetch_intro.parse_vtt(VTT)
    out = fetch_intro.format_intro(fetch_intro.intro_lines(cues, 60))
    assert out.splitlines()[0].startswith("00:00 ")
    assert "Anthropic just dropped" in out


def test_chapters_from_json():
    payload = {"chapters": [
        {"start_time": 0.0, "title": "Intro"},
        {"start_time": 80.5, "title": "Demo"},
    ]}
    ch = fetch_intro.chapters_from_json(payload)
    assert ch == [{"start_sec": 0, "title": "Intro"},
                  {"start_sec": 80, "title": "Demo"}]


def test_chapters_from_json_missing():
    assert fetch_intro.chapters_from_json({}) == []
    assert fetch_intro.chapters_from_json({"chapters": None}) == []


def test_pick_sub_lang_prefers_manual_over_auto():
    meta = {"language": "ru",
            "subtitles": {"ru": [{}]},
            "automatic_captions": {"ru-orig": [{}], "en": [{}]}}
    assert fetch_intro.pick_sub_lang(meta) == "ru"


def test_pick_sub_lang_takes_original_auto_track():
    # русский ролик: en-дорожка это ПЕРЕВОД на лету — просить её нельзя,
    # YouTube отдаёт 429 и роняет весь вызов
    meta = {"language": "ru",
            "automatic_captions": {"en": [{}], "ru-orig": [{}], "de": [{}]}}
    assert fetch_intro.pick_sub_lang(meta) == "ru-orig"


def test_pick_sub_lang_falls_back_to_video_language():
    meta = {"language": "en", "automatic_captions": {"en": [{}], "fr": [{}]}}
    assert fetch_intro.pick_sub_lang(meta) == "en"


def test_pick_sub_lang_without_metadata():
    assert fetch_intro.pick_sub_lang({}) == "en"


def test_fetch_requests_single_original_track(tmp_path):
    """Скрипт обязан просить ОДНУ дорожку, иначе перевод на лету даёт 429."""
    seen = {}

    def runner(cmd, **kwargs):
        if "-J" in cmd:
            return json.dumps({"title": "T", "chapters": [], "language": "ru",
                               "automatic_captions": {"ru-orig": [{}],
                                                      "en": [{}]}})
        seen["langs"] = cmd[cmd.index("--sub-langs") + 1]
        (tmp_path / "vid.ru-orig.vtt").write_text(VTT, encoding="utf-8")
        return ""

    fetch_intro.fetch("vid", runner=runner, workdir=tmp_path)
    assert seen["langs"] == "ru-orig"
    assert "," not in seen["langs"]


def test_fetch_degrades_when_no_subtitles(tmp_path):
    def runner(cmd, **kwargs):
        # -J отдаёт метаданные, скачивание субтитров ничего не создаёт
        if "-J" in cmd:
            return json.dumps({"chapters": [], "title": "T"})
        return ""

    out = fetch_intro.fetch("vid", runner=runner, workdir=tmp_path)
    assert out["subtitles_available"] is False
    assert out["intro"] == ""
    assert out["chapters"] == []


def test_fetch_reads_downloaded_vtt(tmp_path):
    def runner(cmd, **kwargs):
        if "-J" in cmd:
            return json.dumps({"chapters": [
                {"start_time": 0, "title": "Intro"}], "title": "T"})
        (tmp_path / "vid.en.vtt").write_text(VTT, encoding="utf-8")
        return ""

    out = fetch_intro.fetch("vid", runner=runner, workdir=tmp_path)
    assert out["subtitles_available"] is True
    assert "Anthropic just dropped" in out["intro"]
    assert out["chapters"][0]["title"] == "Intro"
