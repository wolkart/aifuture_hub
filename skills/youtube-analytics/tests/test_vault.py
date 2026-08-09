from pathlib import Path

import vault

CHANNEL = {"title": "Nick Saraev", "handle": "nicksaraev",
           "subscribers": 492000, "channel_id": "UCx"}


def _video(vid="v1", title="I Spent $400 Benching Opus-5", kind="long"):
    return {
        "id": vid, "title": title, "kind": kind,
        "url": "https://www.youtube.com/watch?v=" + vid,
        "date": "2026-07-24", "duration_sec": 953,
        "views": 62875, "likes": 1577, "comments": 165,
        "median_multiple": 2.4, "views_per_day": 4000.0,
        "engagement_rate": 0.0277,
        "description": "текст описания", "tags": ["ai"],
        "thumbnail_url": "http://t/h.jpg", "tier2_status": "skeleton",
    }


def _data(videos=None):
    return {"channel": CHANNEL, "videos": videos or [_video()],
            "collected_at": "2026-08-09", "quota_units": 4}


def test_short_title_cuts_on_word_boundary():
    out = vault.short_title("I Spent $400 Benching Opus-5 And Here Is What "
                            "It Can Actually Do For You", limit=30)
    assert len(out) <= 30
    assert not out.endswith(" ")
    assert "|" not in out


def test_short_title_escapes_pipe():
    assert "|" not in vault.short_title("До | После")


def test_card_has_frontmatter_and_backlink():
    md = vault.card_markdown(_video(), CHANNEL)
    assert md.startswith("---\n")
    assert "median_multiple: 2.4" in md
    assert "tier2_status: skeleton" in md
    assert "[[nicksaraev]]" in md
    assert "## Разбор вступления" in md


def test_index_splits_shorts_and_long():
    data = _data([_video("v1", kind="long"),
                  _video("v2", title="Шорт", kind="short")])
    md = vault.index_markdown(data)
    assert "## Длинные" in md
    assert "## Shorts" in md
    assert "[[cards/v1\\|" in md


def test_write_all_creates_structure(tmp_path):
    paths = vault.write_all(_data(), tmp_path)
    root = Path(paths["channel_dir"])
    assert (root / "index.md").exists()
    assert (root / "cards" / "v1.md").exists()
    assert (root / "export.csv").exists()
    assert root.name == "nicksaraev"


def test_write_all_is_idempotent(tmp_path):
    vault.write_all(_data(), tmp_path)
    vault.write_all(_data(), tmp_path)
    cards = list((tmp_path / "nicksaraev" / "cards").glob("*.md"))
    assert len(cards) == 1


def test_write_all_preserves_enriched_sections(tmp_path):
    vault.write_all(_data(), tmp_path)
    card = tmp_path / "nicksaraev" / "cards" / "v1.md"
    text = card.read_text(encoding="utf-8")
    text = text.replace("## Заметки\n", "## Заметки\nмоя ручная заметка\n")
    card.write_text(text, encoding="utf-8")

    vault.write_all(_data(), tmp_path)
    assert "моя ручная заметка" in card.read_text(encoding="utf-8")


def test_csv_has_all_columns(tmp_path):
    vault.write_all(_data(), tmp_path)
    csv_text = (tmp_path / "nicksaraev" / "export.csv").read_text(
        encoding="utf-8")
    header = csv_text.splitlines()[0]
    for col in ("id", "title", "kind", "median_multiple", "views_per_day",
                "engagement_rate", "tier2_status"):
        assert col in header


def test_write_base_creates_obsidian_base(tmp_path):
    path = Path(vault.write_base(tmp_path))
    assert path.name == "_Разведка YouTube.base"
    text = path.read_text(encoding="utf-8")
    assert "median_multiple" in text
    assert "file.name" in text


def test_card_has_thumbnail_text_section():
    md = vault.card_markdown(_video(), CHANNEL)
    assert "## Текст на превью" in md


def test_card_fills_thumbnail_text_when_known():
    v = _video()
    v["thumbnail_text"] = "БЕСПЛАТНО НАВСЕГДА"
    md = vault.card_markdown(v, CHANNEL)
    assert "БЕСПЛАТНО НАВСЕГДА" in md
