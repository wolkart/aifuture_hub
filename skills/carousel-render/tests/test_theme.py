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
    assert b["подпись"] == ["@your_handle"]
    assert b["бейдж"] == "верх-центр"
    assert b["подпись_позиция"] == "низ-лево"


def test_binding_li_body_has_two_lines(theme_file):
    b = theme.binding(theme.load(theme_file), "LI", "тело")
    assert b["подпись"] == ["Your Name", "Role & Tagline"]
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


def test_ступени_промпта_есть_без_правки_темы(theme_file):
    """Лейаут появился позже темы автора: требовать ключ — сломать все темы."""
    data = theme.load(theme_file)
    assert theme.steps(data, "промпт") == theme.DEFAULT_STEPS["промпт"]


def test_тема_перебивает_ступени_по_умолчанию(theme_file):
    data = theme.load(theme_file)
    data.setdefault("ступени", {})["промпт"] = [40, 34, 30]
    assert theme.steps(data, "промпт") == [40, 34, 30]


def test_неизвестная_роль_падает_понятно(theme_file):
    data = theme.load(theme_file)
    with pytest.raises(KeyError):
        theme.steps(data, "выдуманная_роль")


def test_обвязка_промпта_уезжает_вниз_по_умолчанию(theme_file):
    """Сверху на плотной карточке места нет — там текст."""
    data = theme.load(theme_file)
    got = theme.binding(data, "IG", "промпт")
    assert got["бейдж"] == "низ-право"
    assert got["подпись_позиция"] == "низ-лево"
