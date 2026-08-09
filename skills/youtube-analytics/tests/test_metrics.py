import datetime

import metrics


def test_parse_duration_full():
    assert metrics.parse_duration("PT6H2M49S") == 21769


def test_parse_duration_minutes_seconds():
    assert metrics.parse_duration("PT15M53S") == 953


def test_parse_duration_seconds_only():
    assert metrics.parse_duration("PT45S") == 45


def test_parse_duration_with_days():
    assert metrics.parse_duration("P1DT2H") == 93600


def test_parse_duration_garbage_is_zero():
    assert metrics.parse_duration("") == 0
    assert metrics.parse_duration(None) == 0


def test_classify_kind_boundary():
    assert metrics.classify_kind(180) == "short"
    assert metrics.classify_kind(181) == "long"
    assert metrics.classify_kind(45) == "short"


def test_medians_by_kind_separates_types():
    records = [
        {"kind": "short", "views": 100},
        {"kind": "short", "views": 300},
        {"kind": "long", "views": 1000},
        {"kind": "long", "views": 3000},
        {"kind": "long", "views": 5000},
    ]
    result = metrics.medians_by_kind(records)
    assert result["short"] == 200
    assert result["long"] == 3000


def test_medians_by_kind_missing_type():
    result = metrics.medians_by_kind([{"kind": "long", "views": 10}])
    assert result["long"] == 10
    assert result["short"] is None


def test_median_multiple_rounds():
    assert metrics.median_multiple(3000, 1200) == 2.5


def test_median_multiple_zero_median_is_none():
    assert metrics.median_multiple(3000, 0) is None
    assert metrics.median_multiple(3000, None) is None


def test_views_per_day_minimum_one_day():
    today = datetime.date(2026, 8, 9)
    # опубликовано сегодня — делим на 1 день, а не на 0
    assert metrics.views_per_day(500, "2026-08-09", today) == 500.0


def test_views_per_day_counts_elapsed():
    today = datetime.date(2026, 8, 9)
    assert metrics.views_per_day(1000, "2026-07-30", today) == 100.0


def test_engagement_rate():
    assert metrics.engagement_rate(80, 20, 10000) == 0.01


def test_engagement_rate_no_views_is_none():
    assert metrics.engagement_rate(80, 20, 0) is None


def test_enrich_records_adds_all_derived_fields():
    today = datetime.date(2026, 8, 9)
    records = [
        {"id": "a", "kind": "long", "views": 3000, "likes": 100,
         "comments": 50, "date": "2026-07-30"},
        {"id": "b", "kind": "long", "views": 1000, "likes": 10,
         "comments": 5, "date": "2026-07-30"},
    ]
    out = metrics.enrich_records(records, today)
    assert out[0]["median_multiple"] == 1.5
    assert out[1]["median_multiple"] == 0.5
    assert out[0]["views_per_day"] == 300.0
    assert out[0]["engagement_rate"] == 0.05
