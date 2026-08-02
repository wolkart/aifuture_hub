import json
from pathlib import Path

import pytest

import carousel_render


@pytest.fixture
def slides_json(tmp_path):
    spec = {
        "meta": {"название": "Тест", "площадка": "LI", "тема": "t.json"},
        "слайды": [
            {"№": 1, "лейаут": "обложка", "заголовок": "Раз"},
            {"№": 2, "лейаут": "тело", "блоки": ["Два"]},
        ],
    }
    p = tmp_path / "slides.json"
    p.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return p


def test_output_dir_prefers_env(slides_json, tmp_path):
    got = carousel_render.output_dir(slides_json, str(tmp_path / "вывод"), "Тест")
    assert got == tmp_path / "вывод" / "Тест"


def test_output_dir_falls_back_next_to_json(slides_json):
    got = carousel_render.output_dir(slides_json, None, "Тест")
    assert got == slides_json.parent / "Тест"


def test_output_dir_ignores_empty_env(slides_json):
    got = carousel_render.output_dir(slides_json, "", "Тест")
    assert got == slides_json.parent / "Тест"


def test_report_lists_counts_and_paths():
    result = {"папка": Path("/tmp/Тест"), "слайды": [
        {"№": 1, "png": Path("/tmp/Тест/01.png"), "ступень": 0,
         "переполнение": 0, "недобор_символов": 0},
        {"№": 2, "png": Path("/tmp/Тест/02.png"), "ступень": 1,
         "переполнение": 0, "недобор_символов": 0},
    ], "простыня": Path("/tmp/Тест/contact-sheet.png"), "проблемы": []}
    text = carousel_render.format_report(result)
    assert "2" in text
    assert "/tmp/Тест" in text
    assert "слайд 2" in text and "ступен" in text


def test_report_does_not_mention_slides_on_top_step():
    """Отчёт короткий: про то, что прошло без правок, писать нечего."""
    result = {"папка": Path("/tmp/Т"), "слайды": [
        {"№": 1, "png": Path("/tmp/Т/01.png"), "ступень": 0,
         "переполнение": 0, "недобор_символов": 0},
    ], "простыня": None, "проблемы": []}
    text = carousel_render.format_report(result)
    assert "слайд 1" not in text


def test_report_shows_overflow_with_char_count():
    result = {"папка": Path("/tmp/Т"), "слайды": [
        {"№": 4, "png": Path("/tmp/Т/04.png"), "ступень": 2,
         "переполнение": 140, "недобор_символов": 68},
    ], "простыня": Path("/tmp/Т/contact-sheet.png"), "проблемы": []}
    text = carousel_render.format_report(result)
    assert "слайд 4" in text
    assert "68" in text
    assert "сократи" in text


def test_report_lists_missing_assets():
    result = {"папка": Path("/tmp/Т"), "слайды": [], "простыня": None,
              "проблемы": ["ассет «спарк» не найден: /nope/spark.svg"]}
    text = carousel_render.format_report(result)
    assert "спарк" in text


@pytest.mark.integration
def test_run_produces_pngs_and_sheet(slides_json, theme_file, tmp_path):
    """Полный прогон: PNG нужного размера, простыня, пустой список проблем."""
    import render

    result = carousel_render.run(slides_json, theme_file, tmp_path / "out",
                                 keep_png=True)
    assert len(result["слайды"]) == 2
    for item in result["слайды"]:
        assert item["png"].exists()
        assert render.png_size(item["png"]) == (1080, 1350)
    assert result["простыня"].exists()
    assert result["проблемы"] == []


def test_linkedin_отдаёт_документ_без_карточек(slides_json, theme_file, tmp_path):
    """LinkedIn грузит PDF. Семнадцать PNG рядом — это мусор, в котором
    легко залить не тот файл."""
    result = carousel_render.run(slides_json, theme_file, tmp_path / "out")
    assert result["документ"].exists()
    assert result["карточки_убраны"] is True
    assert not any(item["png"].exists() for item in result["слайды"])
    assert result["простыня"].exists(), "простыня остаётся: по ней проверяют глазами"


def test_флаг_png_оставляет_карточки(slides_json, theme_file, tmp_path):
    result = carousel_render.run(slides_json, theme_file, tmp_path / "out",
                                 keep_png=True)
    assert result["карточки_убраны"] is False
    assert all(item["png"].exists() for item in result["слайды"])


def test_инстаграм_карточки_не_трогает(slides_json, theme_file, tmp_path):
    """В IG грузят именно картинки — удалять их нельзя даже с --pdf."""
    spec = json.loads(slides_json.read_text(encoding="utf-8"))
    spec["meta"]["площадка"] = "IG"
    slides_json.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    result = carousel_render.run(slides_json, theme_file, tmp_path / "out",
                                 pdf_doc=True)
    assert result["документ"].exists()
    assert result["карточки_убраны"] is False
    assert all(item["png"].exists() for item in result["слайды"])


def test_отчёт_говорит_куда_делись_карточки():
    отчёт = carousel_render.format_report(
        {"папка": Path("/тут"), "слайды": [], "простыня": None,
         "документ": Path("/тут/док.pdf"), "карточки_убраны": True})
    assert "--png" in отчёт


@pytest.mark.integration
def test_run_is_deterministic(slides_json, theme_file, tmp_path):
    """Один и тот же вход даёт побайтово те же PNG."""
    first = carousel_render.run(slides_json, theme_file, tmp_path / "a", keep_png=True)
    second = carousel_render.run(slides_json, theme_file, tmp_path / "b", keep_png=True)
    for a, b in zip(first["слайды"], second["слайды"]):
        assert a["png"].read_bytes() == b["png"].read_bytes(), f"слайд {a['№']} разъехался"


def test_preview_page_embeds_every_slide():
    html = carousel_render.preview_page(["01.html", "02.html", "03.html"], 1080, 1350)
    assert html.count("<iframe") == 3
    assert "_html/01.html" in html


def test_preview_page_scales_cards_to_cell():
    html = carousel_render.preview_page(["01.html"], 1080, 1350)
    assert f"transform:scale({460 / 1080:.6f})" in html
    assert "width:1080px;height:1350px" in html


def test_report_mentions_preview_when_present():
    result = {"папка": Path("/tmp/Т"), "слайды": [], "простыня": None,
              "превью": Path("/tmp/Т/превью.html"), "проблемы": []}
    assert "превью.html" in carousel_render.format_report(result)


def test_report_omits_preview_when_absent():
    result = {"папка": Path("/tmp/Т"), "слайды": [], "простыня": None,
              "превью": None, "проблемы": []}
    assert "Превью" not in carousel_render.format_report(result)


@pytest.mark.integration
def test_run_with_preview_keeps_html(slides_json, theme_file, tmp_path):
    """С флагом превью промежуточный HTML остаётся рядом с PNG."""
    result = carousel_render.run(slides_json, theme_file, tmp_path / "out", preview=True)
    assert result["превью"].exists()
    kept = sorted((tmp_path / "out" / "_html").glob("*.html"))
    assert [p.name for p in kept] == ["01.html", "02.html"]
    for p in kept:
        assert "data:font/ttf" in p.read_text(encoding="utf-8")


@pytest.mark.integration
def test_run_without_preview_leaves_no_html(slides_json, theme_file, tmp_path):
    result = carousel_render.run(slides_json, theme_file, tmp_path / "out")
    assert result["превью"] is None
    assert not (tmp_path / "out" / "_html").exists()
