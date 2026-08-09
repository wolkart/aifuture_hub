import fetch_thumbs

OCR_OUT = """=== aaa.jpg
БЕСПЛАТНО
НАВСЕГДА
=== bbb.jpg
просто текст без признаков
"""


def _data():
    return {
        "channel": {"title": "T", "handle": "t"},
        "videos": [
            {"id": "aaa", "thumbnail_url": "http://t/a.jpg",
             "median_multiple": 4.0, "title": "A"},
            {"id": "bbb", "thumbnail_url": "http://t/b.jpg",
             "median_multiple": 0.5, "title": "B"},
            {"id": "ccc", "thumbnail_url": "", "median_multiple": 1.0,
             "title": "C"},
        ],
    }


def test_ocr_available_needs_macos_and_swiftc():
    assert fetch_thumbs.ocr_available("darwin", lambda c: "/usr/bin/swiftc")
    assert not fetch_thumbs.ocr_available("linux", lambda c: "/usr/bin/swiftc")
    assert not fetch_thumbs.ocr_available("darwin", lambda c: None)


def test_download_all_skips_videos_without_thumbnail(tmp_path):
    got = []

    def fetcher(url, path):
        got.append(url)
        open(path, "wb").write(b"jpg")

    ids = fetch_thumbs.download_all(_data()["videos"], tmp_path, fetcher)
    assert ids == ["aaa", "bbb"]
    assert len(got) == 2


def test_download_all_survives_single_failure(tmp_path):
    def fetcher(url, path):
        if "b.jpg" in url:
            raise IOError("сеть отвалилась")
        open(path, "wb").write(b"jpg")

    ids = fetch_thumbs.download_all(_data()["videos"], tmp_path, fetcher)
    # один упал — остальные собраны, а не потеряны
    assert ids == ["aaa"]


def test_build_returns_slices_and_texts(tmp_path):
    def fetcher(url, path):
        open(path, "wb").write(b"jpg")

    def ocr_runner(paths):
        return OCR_OUT

    out = fetch_thumbs.build(_data(), ocr_runner=ocr_runner, fetcher=fetcher,
                             work_dir=tmp_path)
    assert out["covered"] == 2
    assert out["total"] == 3
    assert out["texts"]["aaa"] == "БЕСПЛАТНО НАВСЕГДА"
    assert out["slices"]["бесплатно"]["n"] == 1
    assert out["slices"]["бесплатно"]["median_multiple"] == 4.0


def test_build_deletes_downloaded_thumbnails(tmp_path):
    """Превью не хранятся — то же правило, что «видео не храним»."""
    def fetcher(url, path):
        open(path, "wb").write(b"jpg")

    fetch_thumbs.build(_data(), ocr_runner=lambda p: OCR_OUT,
                       fetcher=fetcher, work_dir=tmp_path)
    assert list(tmp_path.glob("*.jpg")) == []


def test_build_without_ocr_returns_honest_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch_thumbs, "ocr_available", lambda *a: False)
    out = fetch_thumbs.build(_data(), ocr_runner=None,
                             fetcher=lambda u, p: None, work_dir=tmp_path)
    assert out["covered"] == 0
    assert out["slices"] == {}
    assert "macOS" in out["skipped"]
