import pytest

import fetch_channel


def test_read_env_ignores_comments_and_quotes(tmp_path):
    p = tmp_path / ".env"
    p.write_text(
        '# комментарий\n'
        'YOUTUBE_API_KEY="abc 123"\n'
        "YT_OUTPUT_DIR=/path/with space/dir\n"
        "\n",
        encoding="utf-8")
    env = fetch_channel.read_env(p)
    assert env["YOUTUBE_API_KEY"] == "abc 123"
    assert env["YT_OUTPUT_DIR"] == "/path/with space/dir"


def test_read_env_missing_file_is_empty(tmp_path):
    assert fetch_channel.read_env(tmp_path / "нет.env") == {}


def test_require_key_raises_with_instruction(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        fetch_channel.require_key({})
    assert "YOUTUBE_API_KEY" in str(exc.value)


def _fake_getter(pages):
    """Отдаёт заранее заготовленные ответы по порядку вызовов."""
    calls = []

    def getter(endpoint, params, key):
        calls.append((endpoint, params))
        return pages.pop(0)
    getter.calls = calls
    return getter


def test_collect_walks_playlist_and_counts_quota():
    channel_page = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@t"},
        "statistics": {"subscriberCount": "100"},
        "contentDetails": {"relatedPlaylists": {"uploads": "UUx"}},
    }]}
    playlist_page1 = {
        "items": [{"contentDetails": {"videoId": "v1"}},
                  {"contentDetails": {"videoId": "v2"}}],
        "nextPageToken": "T2",
    }
    playlist_page2 = {"items": [{"contentDetails": {"videoId": "v3"}}]}

    def video_item(vid, dur, views):
        return {
            "id": vid,
            "snippet": {"publishedAt": "2026-07-01T00:00:00Z", "title": vid,
                        "description": "", "thumbnails": {}},
            "statistics": {"viewCount": str(views), "likeCount": "1",
                           "commentCount": "1"},
            "contentDetails": {"duration": dur},
        }

    videos_page = {"items": [video_item("v1", "PT10M", 1000),
                             video_item("v2", "PT10M", 3000),
                             video_item("v3", "PT30S", 500)]}

    getter = _fake_getter([channel_page, playlist_page1,
                           playlist_page2, videos_page])
    result = fetch_channel.collect("@t", "KEY", limit=300, getter=getter)

    assert result["channel"]["handle"] == "t"
    assert len(result["videos"]) == 3
    # 1 channels + 2 playlistItems + 1 videos
    assert result["quota_units"] == 4
    # производные поля посчитаны, медианы раздельные
    by_id = {v["id"]: v for v in result["videos"]}
    assert by_id["v2"]["median_multiple"] == 1.5
    assert by_id["v3"]["median_multiple"] == 1.0
    # search.list не вызывался ни разу
    assert all(ep != "search" for ep, _ in getter.calls)


def test_collect_respects_limit():
    channel_page = {"items": [{
        "id": "UCx", "snippet": {"title": "T", "customUrl": "@t"},
        "statistics": {}, "contentDetails": {
            "relatedPlaylists": {"uploads": "UUx"}}}]}
    playlist_page = {
        "items": [{"contentDetails": {"videoId": "v%d" % i}}
                  for i in range(50)],
        "nextPageToken": "MORE",
    }
    videos_page = {"items": [{
        "id": "v0",
        "snippet": {"publishedAt": "2026-07-01T00:00:00Z", "title": "v0",
                    "description": "", "thumbnails": {}},
        "statistics": {"viewCount": "10"},
        "contentDetails": {"duration": "PT10M"}}]}
    getter = _fake_getter([channel_page, playlist_page, videos_page])
    result = fetch_channel.collect("@t", "KEY", limit=2, getter=getter)
    # лимит обрезает список id ДО запроса videos — вторая страница не берётся
    assert len(getter.calls) == 3
    assert result["requested_limit"] == 2
