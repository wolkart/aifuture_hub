import patterns


def test_has_timecodes_detects_chapter_block():
    desc = "Мой канал\n00:00 Intro\n01:20 Demo\n05:00 Итог"
    assert patterns.has_timecodes(desc) is True


def test_has_timecodes_ignores_inline_time():
    assert patterns.has_timecodes("это заняло 10:30 утра, представь") is False


def test_has_timecodes_needs_two_marks():
    assert patterns.has_timecodes("00:00 Intro") is False


def test_title_features_flags():
    f = patterns.title_features("I Spent $400 Benching Opus-5 (2026)")
    assert f["has_digit"] is True
    assert f["has_year_tag"] is True
    assert f["has_brackets"] is True
    assert f["has_question"] is False


def test_title_features_caps_word():
    assert patterns.title_features("CLAUDE CODE FULL COURSE")["has_caps"] is True
    assert patterns.title_features("Claude Code course")["has_caps"] is False


def test_title_features_short_caps_not_counted():
    # аббревиатуры вроде AI/API — не «капслок-приём»
    assert patterns.title_features("What is AI now")["has_caps"] is False


def test_bucket_picks_range():
    edges = [(0, 40, "≤40"), (41, 60, "41–60"), (61, 9999, "61+")]
    assert patterns.bucket(35, edges) == "≤40"
    assert patterns.bucket(41, edges) == "41–60"
    assert patterns.bucket(900, edges) == "61+"


def test_slice_stats_marks_small_groups_unreliable():
    records = [{"median_multiple": 1.0, "g": "a"}] * 3 + \
              [{"median_multiple": 2.0, "g": "b"}] * 6
    stats = patterns.slice_stats(records, lambda r: r["g"])
    assert stats["a"]["n"] == 3
    assert stats["a"]["reliable"] is False
    assert stats["b"]["n"] == 6
    assert stats["b"]["reliable"] is True
    assert stats["b"]["median_multiple"] == 2.0


def test_by_month_separates_kinds():
    records = [
        {"date": "2026-07-02", "kind": "long", "views": 100},
        {"date": "2026-07-20", "kind": "long", "views": 300},
        {"date": "2026-07-05", "kind": "short", "views": 1000},
        {"date": "2026-06-01", "kind": "long", "views": 50},
    ]
    out = patterns.by_month(records)
    assert out["2026-07"]["long"]["median_views"] == 200
    assert out["2026-07"]["short"]["median_views"] == 1000
    assert out["2026-06"]["long"]["n"] == 1


def test_build_report_has_all_seven_slices():
    data = {
        "channel": {"title": "T", "handle": "t", "subscribers": 1000},
        "videos": [
            {"id": "v%d" % i, "title": "Заголовок номер %d" % i,
             "date": "2026-07-%02d" % (i + 1), "kind": "long",
             "views": 100 * (i + 1), "duration_sec": 600,
             "description": "00:00 a\n01:00 b", "median_multiple": 1.0 * i,
             "engagement_rate": 0.01, "views_per_day": 10.0}
            for i in range(12)
        ],
    }
    report = patterns.build_report(data)
    for key in ("by_month", "title_length", "title_composition",
                "duration", "description", "extremes", "rhythm"):
        assert key in report
    assert len(report["extremes"]["top"]) <= 15
    assert len(report["extremes"]["bottom"]) <= 15


def test_render_markdown_ends_with_takeaways_section():
    data = {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}
    md = patterns.render_markdown(patterns.build_report(data), data["channel"])
    assert "## Что забираем себе" in md
    # секция «Что забираем себе» — последняя, её не перекрывают другие срезы
    assert md.index("## Что забираем себе") > md.index("## 7. Ритм публикаций")


def _one_video_data():
    return {"channel": {"title": "T", "handle": "t", "subscribers": 1},
            "videos": [{"id": "a", "title": "t", "date": "2026-07-01",
                        "kind": "long", "views": 10, "duration_sec": 600,
                        "description": "", "median_multiple": 1.0,
                        "engagement_rate": 0.01, "views_per_day": 1.0}]}


def test_render_markdown_adds_thumbnail_section_when_given():
    data = _one_video_data()
    thumbs = {"covered": 40, "total": 47, "skipped": "",
              "slices": {"бесплатно": {"n": 6, "median_multiple": 3.75,
                                       "median_without": 0.96,
                                       "reliable": True}}}
    md = patterns.render_markdown(patterns.build_report(data),
                                  data["channel"], thumbs)
    assert "## 8. Текст на превью" in md
    assert "3.75" in md
    assert "0.96" in md
    # раздел «Что забираем себе» остаётся последним
    assert md.index("## Что забираем себе") > md.index("## 8. Текст на превью")


def test_render_markdown_without_thumbs_has_no_section():
    data = _one_video_data()
    md = patterns.render_markdown(patterns.build_report(data), data["channel"])
    assert "Текст на превью" not in md


def test_render_markdown_reports_skipped_ocr():
    data = _one_video_data()
    thumbs = {"covered": 0, "total": 47,
              "skipped": "OCR недоступен: нужен macOS", "slices": {}}
    md = patterns.render_markdown(patterns.build_report(data),
                                  data["channel"], thumbs)
    assert "OCR недоступен" in md
