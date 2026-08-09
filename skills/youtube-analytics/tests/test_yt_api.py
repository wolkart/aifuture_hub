import json

import pytest

import yt_api


def test_chunked_splits_by_fifty():
    items = list(range(120))
    chunks = list(yt_api.chunked(items, 50))
    assert [len(c) for c in chunks] == [50, 50, 20]


def test_chunked_empty():
    assert list(yt_api.chunked([], 50)) == []


def test_resolve_channel_reads_uploads_playlist():
    payload = {"items": [{
        "id": "UCabc",
        "snippet": {"title": "Nick Saraev", "customUrl": "@nicksaraev"},
        "statistics": {"subscriberCount": "492000"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUabc"}},
    }]}
    ch = yt_api.resolve_channel(payload)
    assert ch["channel_id"] == "UCabc"
    assert ch["handle"] == "nicksaraev"
    assert ch["subscribers"] == 492000
    assert ch["uploads_playlist"] == "UUabc"


def test_resolve_channel_empty_raises():
    with pytest.raises(LookupError):
        yt_api.resolve_channel({"items": []})


def test_resolve_channel_hidden_subscribers():
    payload = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@x"},
        "statistics": {},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}},
    }]}
    assert yt_api.resolve_channel(payload)["subscribers"] is None


def test_parse_playlist_page_returns_ids_and_token():
    payload = {
        "items": [
            {"contentDetails": {"videoId": "aaa"}},
            {"contentDetails": {"videoId": "bbb"}},
        ],
        "nextPageToken": "TOKEN2",
    }
    ids, token = yt_api.parse_playlist_page(payload)
    assert ids == ["aaa", "bbb"]
    assert token == "TOKEN2"


def test_parse_playlist_page_last_page_has_no_token():
    ids, token = yt_api.parse_playlist_page(
        {"items": [{"contentDetails": {"videoId": "z"}}]})
    assert token is None


def test_best_thumbnail_prefers_maxres():
    thumbs = {"default": {"url": "d"}, "high": {"url": "h"},
              "maxres": {"url": "m"}}
    assert yt_api.best_thumbnail(thumbs) == "m"


def test_best_thumbnail_falls_back():
    assert yt_api.best_thumbnail({"default": {"url": "d"}}) == "d"
    assert yt_api.best_thumbnail({}) == ""


def test_parse_videos_maps_fields():
    payload = {"items": [{
        "id": "vid1",
        "snippet": {
            "publishedAt": "2026-07-24T14:00:00Z",
            "title": "I Spent $400 Benching Opus-5",
            "description": "line one\n00:00 Intro\n01:20 Demo",
            "tags": ["ai", "claude"],
            "thumbnails": {"high": {"url": "http://t/h.jpg"}},
        },
        "statistics": {"viewCount": "62875", "likeCount": "1577",
                       "commentCount": "165"},
        "contentDetails": {"duration": "PT15M53S"},
    }]}
    rows = yt_api.parse_videos(payload)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == "vid1"
    assert r["title"] == "I Spent $400 Benching Opus-5"
    assert r["date"] == "2026-07-24"
    assert r["views"] == 62875
    assert r["likes"] == 1577
    assert r["comments"] == 165
    assert r["duration_sec"] == 953
    assert r["kind"] == "long"
    assert r["tags"] == ["ai", "claude"]
    assert r["thumbnail_url"] == "http://t/h.jpg"
    assert r["url"] == "https://www.youtube.com/watch?v=vid1"


def test_parse_videos_hidden_likes_are_none():
    payload = {"items": [{
        "id": "v2",
        "snippet": {"publishedAt": "2026-01-01T00:00:00Z", "title": "t",
                    "description": "", "thumbnails": {}},
        "statistics": {"viewCount": "10"},
        "contentDetails": {"duration": "PT30S"},
    }]}
    r = yt_api.parse_videos(payload)[0]
    assert r["likes"] is None
    assert r["comments"] is None
    assert r["tags"] == []
    assert r["kind"] == "short"


def test_parse_comments_sorts_by_likes():
    payload = {"items": [
        {"snippet": {"topLevelComment": {"snippet": {
            "textOriginal": "мало", "likeCount": 2,
            "authorDisplayName": "a"}}}},
        {"snippet": {"topLevelComment": {"snippet": {
            "textOriginal": "много", "likeCount": 40,
            "authorDisplayName": "b"}}}},
    ]}
    out = yt_api.parse_comments(payload)
    assert [c["text"] for c in out] == ["много", "мало"]
    assert out[0]["likes"] == 40


def test_api_get_builds_url_and_never_leaks_key():
    seen = {}

    def fake_opener(url, timeout=None):
        seen["url"] = url

        class R:
            def read(self):
                return json.dumps({"ok": True}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()

    data = yt_api.api_get("videos", {"id": "abc"}, "SECRETKEY",
                          opener=fake_opener)
    assert data == {"ok": True}
    assert "youtube/v3/videos" in seen["url"]
    assert "id=abc" in seen["url"]
    assert "key=SECRETKEY" in seen["url"]
    # ключ в URL нужен, но в человекочитаемой ошибке его быть не должно
    assert "SECRETKEY" not in yt_api.safe_url(seen["url"])
