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
             "заголовок": "Три шага\nвместо\nдесяти",
             "подзаголовок": "Звучит как высшая математика."}
    got = build_html.build(slide, data, "LI",
                           {"заголовок": 200, "подзаголовок": 56}, theme_dir)
    assert "<link" not in got
    assert 'src="http' not in got
    assert "url(http" not in got


def test_build_renders_forced_line_breaks(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Три шага\nвместо"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Три шага<br>вместо" in got


def test_build_applies_accent_on_cover(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Я отдал **Claude**"}
    got = build_html.build(slide, data, "LI", {"заголовок": 150}, theme_dir)
    assert '<b class="акцент">Claude</b>' in got


def test_build_puts_li_signature_in_two_lines(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "LI", {"заголовок": 200}, theme_dir)
    assert "Your Name" in got
    assert "Role &amp; Tagline" in got


def test_build_puts_ig_signature_in_one_line(data, theme_dir):
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "Тест"}
    got = build_html.build(slide, data, "IG", {"заголовок": 200}, theme_dir)
    assert "@your_handle" in got
    assert "Role" not in got


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
    assert "Your Name" in got


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
        "промпт": {"заголовок": "Т", "промпт": "Сделай [ЧТО-ТО]"},
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


# ── воздух под диакритику ─────────────────────────────────────────────────

@pytest.mark.parametrize("заголовок,ожидание", [
    ("ТРЕТИЙ ДЕНЬ", True),
    ("третий день", True),      # обложка набирается капсом через CSS
    ("ВСЁ СЛОМАЕТСЯ", True),
    ("ТРИ ДНЯ", False),
    ("", False),
])
def test_высокий_знак_опознаётся(заголовок, ожидание):
    assert build_html.нужен_воздух(заголовок) is ожидание


def база_интерлиньяжа(data):
    """То же значение, что берёт build: тема, иначе дефолт CSS."""
    return float(data.get("типографика", {}).get("интерлиньяж_обложки", 0.95))


def сколько_объявлений(html):
    """Считаем именно ОБЪЯВЛЕНИЯ в :root (с двоеточием), а не обращения
    `var(--интерлиньяж-обложки, …)` внутри cover.css."""
    return html.count("--интерлиньяж-обложки:")


def test_обложка_с_краткой_получает_больше_интерлиньяжа(data, theme_dir):
    """«Й» поднимается над капслоком и при базовом интерлиньяже почти
    касается строки сверху — заголовку нужен воздух."""
    slide = {"№": 1, "лейаут": "обложка", "заголовок": "БРОСАЮТ НА\nТРЕТИЙ ДЕНЬ"}
    html = build_html.build(slide, data, "IG", {"заголовок": 140}, theme_dir)
    значение = float(html.split("--интерлиньяж-обложки:")[-1].split(";")[0])
    ожидание = round(база_интерлиньяжа(data) + build_html.ДОБАВКА_ИНТЕРЛИНЬЯЖА, 3)
    assert значение == ожидание
    assert значение > база_интерлиньяжа(data)


def test_обложка_без_диакритики_идёт_на_теме(data, theme_dir):
    """Остальные обложки не должны разъезжаться: тема откалибрована замером."""
    без = {"№": 1, "лейаут": "обложка", "заголовок": "ТРИ ДНЯ"}
    с = {"№": 1, "лейаут": "обложка", "заголовок": "ТРЕТИЙ ДЕНЬ"}
    html_без = build_html.build(без, data, "IG", {"заголовок": 140}, theme_dir)
    html_с = build_html.build(с, data, "IG", {"заголовок": 140}, theme_dir)
    assert сколько_объявлений(html_с) == сколько_объявлений(html_без) + 1


def test_добавка_не_трогает_другие_лейауты(data, theme_dir):
    """У тела свой интерлиньяж, и «Й» в списке на него не влияет."""
    slide = {"№": 2, "лейаут": "тело", "блоки": ["Третий день — и всё"]}
    обложка = {"№": 1, "лейаут": "обложка", "заголовок": "ТРИ ДНЯ"}
    html = build_html.build(slide, data, "IG", {"тело": 78}, theme_dir)
    эталон = build_html.build(обложка, data, "IG", {"заголовок": 140}, theme_dir)
    assert сколько_объявлений(html) == сколько_объявлений(эталон)


# ── лейаут «промпт» ───────────────────────────────────────────────────────

def промпт_слайд(**over):
    slide = {"№": 2, "лейаут": "промпт", "номер": "01",
             "заголовок": "Описание продукта",
             "подзаголовок": "Пока не написано — ты угадываешь.",
             "промпт": "Напиши описание. Код НЕ пиши.\n\nЧто строим: [ОПИШИ ИДЕЮ]"}
    slide.update(over)
    return slide


def test_промпт_собирает_все_части(data, theme_dir):
    html = build_html.build(промпт_слайд(), data, "IG", {"промпт": 30}, theme_dir)
    assert 'class="номер"' in html and ">01<" in html
    assert "Описание продукта" in html
    assert 'class="блок-промпта"' in html


def test_плейсхолдер_подсвечен_а_текст_не_тронут(data, theme_dir):
    """Автор пишет промпт как обычный текст: [СКОБКИ] красятся сами."""
    html = build_html.build(промпт_слайд(), data, "IG", {"промпт": 30}, theme_dir)
    assert '<span class="акцент">[ОПИШИ ИДЕЮ]</span>' in html
    assert "Напиши описание. Код НЕ пиши." in html


def test_переносы_в_промпте_не_превращаются_в_br(data, theme_dir):
    """Переносы держит white-space: pre-wrap — текст в JSON и на карточке один."""
    html = build_html.build(промпт_слайд(), data, "IG", {"промпт": 30}, theme_dir)
    блок = html.split('class="текст"')[1].split("</div>")[0]
    assert "<br>" not in блок
    assert "\n" in блок


def test_номер_необязателен(data, theme_dir):
    html = build_html.build(промпт_слайд(номер=None), data, "IG",
                            {"промпт": 30}, theme_dir)
    assert 'class="номер"' not in html


def test_промпт_требует_свой_кегль(data, theme_dir):
    """Без кегля CSS молча свалится на 16px — это должно быть ошибкой."""
    with pytest.raises(ValueError):
        build_html.build(промпт_слайд(), data, "IG", {}, theme_dir)


def test_разметка_автора_в_промпте_экранируется(data, theme_dir):
    html = build_html.build(промпт_слайд(промпт="Верни <b>жирным</b>"),
                            data, "IG", {"промпт": 30}, theme_dir)
    assert "&lt;b&gt;" in html
