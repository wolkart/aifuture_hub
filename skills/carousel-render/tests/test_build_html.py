import base64

import pytest

import build_html
import theme


@pytest.fixture
def data(theme_file):
    return theme.load(theme_file)


def test_data_uri_encodes_png(theme_dir):
    uri = build_html.data_uri(theme_dir / "assets" / "avatar-ig.png")
    assert uri.startswith("data:image/png;base64,")
    payload = uri.split(",", 1)[1]
    assert base64.b64decode(payload) == b"\x89PNG\r\n\x1a\nfake"


def test_data_uri_picks_svg_mime(theme_dir):
    uri = build_html.data_uri(theme_dir / "assets" / "spark.svg")
    assert uri.startswith("data:image/svg+xml;base64,")


def test_data_uri_picks_font_mime(theme_dir):
    uri = build_html.data_uri(theme_dir / "fonts" / "Oswald.ttf")
    assert uri.startswith("data:font/ttf;base64,")


def test_font_css_embeds_both_families(data):
    css = build_html.font_css(data)
    assert css.count("@font-face") == 2
    assert "Oswald" in css and "Montserrat" in css
    assert "data:font/ttf;base64," in css
    assert "http" not in css


def test_font_css_declares_weight_range(data):
    """Вариативный шрифт: один файл на все веса."""
    assert "font-weight: 200 900" in build_html.font_css(data)


def test_css_vars_exposes_brand_colors(data):
    css = build_html.css_vars(data, {"заголовок": 200})
    assert "--акцент: #D97757" in css
    assert "--текст-тела: #33336F" in css
    assert "--заголовок: 200px" in css


def test_build_is_self_contained(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка",
             "заголовок": "Агент.\nХарнес.\nLoop.",
             "подзаголовок": "Звучит как высшая математика."}
    got = build_html.build(slide, data, "LI",
                           {"заголовок": 200, "подзаголовок": 56}, theme_dir)
    assert "<link" not in got
    assert 'src="http' not in got
    assert "url(http" not in got


def test_build_renders_forced_line_breaks(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Агент.\nХарнес."}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Агент.<br>Харнес." in got


def test_build_applies_accent_on_cover(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Я отдал **Claude**"}
    got = build_html.build(slide, data, "LI", {"заголовок": 150}, theme_dir)
    assert '<b class="акцент">Claude</b>' in got


def test_build_puts_li_signature_in_two_lines(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Artem Volkov" in got
    assert "AI-Developer &amp; Content Creator" in got


def test_build_puts_ig_signature_in_one_line(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "IG", {"заголовок": 200}, theme_dir)
    assert "@ai_rtem" in got
    assert "AI-Developer" not in got


def test_build_includes_measure_js(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "data-overflow" in got or "dataset.overflow" in got


def test_build_rejects_unknown_layout(data, theme_dir):
    with pytest.raises(ValueError, match="лейаут"):
        build_html.build({"№": 1, "лейаут": "карусель-мечты"}, data, "LI", {}, theme_dir)


def test_body_renders_each_block_as_paragraph(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело",
             "блоки": ["Первый абзац.", "Второй абзац."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert got.count('class="блок"') == 2
    assert "Первый абзац." in got and "Второй абзац." in got


def test_body_bold_uses_accent_class(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["код и **замолчит**."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert '<b class="акцент">замолчит</b>' in got


def test_body_thread_arrow_only_on_last_block(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело",
             "блоки": ["Раз.", "Два.", "Первая её часть"], "нить": True}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert got.count('class="нить"') == 1
    tail = got.split("Первая её часть")[1]
    assert 'class="нить"' in tail.split("</div>")[0]


def test_body_without_thread_has_no_arrow(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Раз."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert 'class="нить"' not in got


def test_body_is_light_card(data, theme_dir):
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Раз."]}
    got = build_html.build(slide, data, "LI", {"тело": 60}, theme_dir)
    assert "карточка светлая" in got


def test_list_renders_title_subtitle_items_footer(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список",
             "заголовок": "Разработка",
             "подзаголовок": "Проект не разваливается на пятой правке.",
             "пункты": ["**superpowers** — не бросишь на середине",
                        "**context7** — код заводится с первого раза"],
             "подвал": "→ Твой отдел разработки"}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert "Разработка" in got
    assert "не разваливается" in got
    assert got.count('class="пункт"') == 2
    assert '<b class="акцент">superpowers</b>' in got
    assert "Твой отдел разработки" in got
    assert 'class="подвал"' in got


def test_list_without_footer_omits_it(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список", "заголовок": "Разработка",
             "пункты": ["**раз** — два"]}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert 'class="подвал"' not in got


def test_list_uses_ig_badge_bottom_right(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список", "заголовок": "Р", "пункты": ["**а** — б"]}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert "бейдж низ-право" in got
    assert "подпись низ-лево" in got
