from pathlib import Path

import check_env
import fonts


def test_check_theme_missing_env():
    ok, msg = check_env.check_theme(None)
    assert ok is False
    assert "THEME_PATH" in msg


def test_check_theme_missing_file(tmp_path):
    ok, msg = check_env.check_theme(str(tmp_path / "нет.json"))
    assert ok is False
    assert "не найден" in msg


def test_check_theme_ok(theme_file):
    ok, msg = check_env.check_theme(str(theme_file))
    assert ok is True


def test_check_fonts_ok(theme_dir):
    ok, msg = check_env.check_fonts(theme_dir)
    assert ok is True


def test_check_fonts_missing(tmp_path):
    (tmp_path / "fonts").mkdir()
    ok, msg = check_env.check_fonts(tmp_path)
    assert ok is False
    assert "Oswald" in msg


def test_report_marks_failures():
    text = check_env.report([("Chrome", True, "есть"), ("Шрифты", False, "нет Oswald")])
    assert "✓ Chrome" in text
    assert "✗ Шрифты" in text
    assert "нет Oswald" in text


def test_font_urls_cover_required():
    assert set(fonts.FONT_URLS) == {"Oswald", "Montserrat"}
    for url in fonts.FONT_URLS.values():
        assert url.startswith("https://")
        assert url.endswith(".ttf")


def test_ensure_fonts_skips_existing(theme_dir):
    # шрифты уже лежат — скачивать нечего
    assert fonts.ensure_fonts(theme_dir, download=False) == []


def test_ensure_fonts_reports_missing(tmp_path):
    got = fonts.ensure_fonts(tmp_path, download=False)
    assert sorted(got) == ["Montserrat", "Oswald"]
