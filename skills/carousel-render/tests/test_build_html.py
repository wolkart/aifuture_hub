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


def test_cta_is_dark_card(data, theme_dir):
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert "карточка тёмная" in got


def test_cta_has_no_badge(data, theme_dir):
    """Проверяем отсутствие элемента, а не слова: «ЛИСТАЙ» есть в комментарии CSS."""
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert 'class="бейдж' not in got
    assert ">ЛИСТАЙ" not in got


def test_cta_signature_sits_on_top(data, theme_dir):
    """На CTA подпись крупная и сверху, а не мелкая внизу."""
    slide = {"№": 7, "лейаут": "CTA", "блоки": ["Подписывайся."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert "подпись верх-центр" in got
    assert "Artem Volkov" in got


def test_cta_renders_all_blocks(data, theme_dir):
    slide = {"№": 7, "лейаут": "CTA",
             "блоки": ["Хочешь разбираться в AI — подписывайся.",
                       "Разбираю по-честному."]}
    got = build_html.build(slide, data, "LI", {"cta": 50}, theme_dir)
    assert got.count('class="блок"') == 2


def test_all_layouts_build(data, theme_dir):
    """Словарь лейаутов закрыт и целиком поддержан."""
    import theme as theme_mod
    samples = {
        "обложка": {"заголовок": "Т"},
        "тело": {"блоки": ["Т"]},
        "тело-список": {"заголовок": "Т", "пункты": ["**а** — б"]},
        "CTA": {"блоки": ["Т"]},
    }
    for layout in theme_mod.LAYOUTS:
        slide = {"№": 1, "лейаут": layout, **samples[layout]}
        sizes = {k: 42 for k in build_html.SIZE_KEYS[layout]}
        got = build_html.build(slide, data, "LI", sizes, theme_dir)
        assert got.startswith("<!doctype")


def test_size_keys_cover_all_layouts():
    import theme as theme_mod
    assert set(build_html.SIZE_KEYS) == set(theme_mod.LAYOUTS)


def test_build_rejects_missing_size(data, theme_dir):
    """Неопределённый var() в CSS даёт 16px молча — ловим это как ошибку."""
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Раз."]}
    with pytest.raises(ValueError, match="16px"):
        build_html.build(slide, data, "LI", {}, theme_dir)


def test_css_vars_passes_typography_without_units(data, theme_dir):
    """Трекинг и интерлиньяж — безразмерные, px к ним приписывать нельзя."""
    data["типографика"] = {"трекинг_обложки": "-0.05em", "интерлиньяж_обложки": "0.95"}
    css = build_html.css_vars(data, {"заголовок": 200})
    assert "--трекинг-обложки: -0.05em;" in css
    assert "--интерлиньяж-обложки: 0.95;" in css


def test_css_vars_survives_theme_without_typography(data):
    """Блок необязательный: у CSS на каждый ключ свой дефолт."""
    assert "трекинг" not in build_html.css_vars(data, {"заголовок": 200})


def test_inline_svg_puts_markup_in_document(theme_dir):
    """SVG вставляется разметкой: только так currentColor берёт цвет страницы."""
    got = build_html.inline_svg(theme_dir / "assets" / "spark.svg", "спарк")
    assert got.startswith('<div class="спарк">')
    assert "<svg" in got
    assert "data:image/svg+xml" not in got


def test_inline_svg_strips_title_and_prolog(tmp_path):
    p = tmp_path / "icon.svg"
    p.write_text('<?xml version="1.0"?><svg viewBox="0 0 10 10">'
                 "<title>Claude Code</title><path d=\"M0 0\"/></svg>", encoding="utf-8")
    got = build_html.inline_svg(p, "спарк")
    assert "<?xml" not in got
    assert "<title>" not in got
    assert "<path" in got


def test_decor_cover_inlines_svg_not_img(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "вид": "декор", "заголовок": "Тест"}
    got = build_html.build(slide, data, "IG", {"заголовок": 150}, theme_dir)
    assert '<div class="спарк"><svg' in got
    assert 'class="спарк" src=' not in got


def test_decor_cover_falls_back_to_img_for_raster(data, theme_dir):
    """Растровый значок тоже поддержан — просто без перекраски."""
    raster = theme_dir / "assets" / "spark.png"
    raster.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    data["ассеты"]["спарк"] = raster
    slide = {"№": 1, "лейаут": "обложка", "вид": "декор", "заголовок": "Тест"}
    got = build_html.build(slide, data, "IG", {"заголовок": 150}, theme_dir)
    assert 'class="спарк" src="data:image/png' in got


def test_binding_is_layered_above_photo_background():
    """Обвязка в разметке идёт раньше фото-фона — без z-index фото её закрасит."""
    css = build_html.layout_css("обложка")
    badge = css.split(".бейдж {")[1].split("}")[0]
    signature = css.split(".подпись {")[1].split("}")[0]
    assert "z-index" in badge
    assert "z-index" in signature


def test_band_classes_marks_both_edges_busy():
    b = {"бейдж": "верх-центр", "подпись_позиция": "низ-центр"}
    assert build_html.band_classes(b, True) == "верх-занят низ-занят"


def test_band_classes_frees_top_when_badge_moved_down():
    """Автор убирает бейдж вниз, чтобы освободить верх — полоса должна сжаться."""
    b = {"бейдж": "низ-право", "подпись_позиция": "низ-лево"}
    assert build_html.band_classes(b, True) == "верх-свободен низ-занят"


def test_band_classes_frees_bottom_on_photo_cover():
    """На фото-обложке подпись погашена, снизу никого — полоса не нужна."""
    b = {"бейдж": "верх-центр", "подпись_позиция": "низ-центр"}
    assert build_html.band_classes(b, False) == "верх-занят низ-свободен"


def test_band_classes_lands_in_markup(data, theme_dir):
    slide = {"№": 4, "лейаут": "тело-список", "заголовок": "Р", "пункты": ["**а** — б"]}
    got = build_html.build(slide, data, "IG", {"тело_список": 42}, theme_dir)
    assert "верх-занят" in got or "верх-свободен" in got


def test_badge_chevron_is_vector_not_glyph():
    """Текстовый «›» в Light-весе выходит тонким и не по центру — нужен вектор."""
    got = build_html._badge_html("верх-центр")
    assert "<svg" in got
    assert "›" not in got
    assert "stroke-width" in got


def test_badge_chevron_inherits_colour():
    """Кружок бывает светлым и тёмным — шеврон должен красться от родителя."""
    assert 'stroke="currentColor"' in build_html.CHEVRON_SVG


def test_badge_hidden_has_no_chevron():
    assert build_html._badge_html("нет") == ""
