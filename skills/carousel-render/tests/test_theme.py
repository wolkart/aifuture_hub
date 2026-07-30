from pathlib import Path

import pytest

import theme


def test_load_resolves_asset_paths(theme_file):
    data = theme.load(theme_file)
    avatar = data["обвязка"]["IG"]["аватар"]
    assert isinstance(avatar, Path)
    assert avatar.is_absolute()
    assert avatar.exists()


def test_load_records_theme_dir(theme_file):
    data = theme.load(theme_file)
    assert data["_dir"] == theme_file.parent


def test_validate_accepts_good_theme(theme_file):
    assert theme.validate(theme.load(theme_file)) == []


def test_validate_reports_missing_color(theme_file):
    data = theme.load(theme_file)
    del data["цвета"]["акцент"]
    problems = theme.validate(data)
    assert any("акцент" in p for p in problems)


def test_validate_reports_missing_asset(theme_file):
    data = theme.load(theme_file)
    data["обвязка"]["IG"]["аватар"] = theme_file.parent / "нет.png"
    problems = theme.validate(data)
    assert any("нет.png" in p for p in problems)


def test_validate_requires_three_steps(theme_file):
    data = theme.load(theme_file)
    data["ступени"]["тело"] = [60]
    problems = theme.validate(data)
    assert any("тело" in p and "ступен" in p for p in problems)


def test_binding_ig_cover(theme_file):
    b = theme.binding(theme.load(theme_file), "IG", "обложка")
    assert b["подпись"] == ["@ai_rtem"]
    assert b["бейдж"] == "верх-центр"
    assert b["подпись_позиция"] == "низ-лево"


def test_binding_li_body_has_two_lines(theme_file):
    b = theme.binding(theme.load(theme_file), "LI", "тело")
    assert b["подпись"] == ["Artem Volkov", "AI-Developer & Content Creator"]
    assert b["подпись_позиция"] == "низ-центр"


def test_binding_unknown_platform_raises(theme_file):
    with pytest.raises(KeyError):
        theme.binding(theme.load(theme_file), "TikTok", "тело")


def test_steps_returns_descending(theme_file):
    got = theme.steps(theme.load(theme_file), "тело")
    assert got == sorted(got, reverse=True)


def test_example_theme_is_valid():
    """Пример темы в репозитории должен грузиться и проходить валидацию."""
    p = Path(__file__).parent.parent / "themes" / "example.json"
    data = theme.load(p)
    problems = [x for x in theme.validate(data) if "не найден" not in x]
    assert problems == []
