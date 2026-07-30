import pytest

import contact_sheet


@pytest.fixture
def pngs(tmp_path):
    out = []
    for i in range(1, 5):
        p = tmp_path / f"{i:02d}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 16)
        out.append(p)
    return out


def test_sheet_html_embeds_every_slide(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    assert html.count("data:image/png;base64,") == 4


def test_sheet_html_has_no_external_requests(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    assert "http" not in html
    assert "file://" not in html


def test_sheet_html_uses_requested_columns(pngs):
    html = contact_sheet.build_sheet_html(pngs, cols=2)
    assert "repeat(2," in html


def test_sheet_html_numbers_slides(pngs):
    html = contact_sheet.build_sheet_html(pngs)
    for n in ("01", "02", "03", "04"):
        assert n in html


@pytest.mark.integration
def test_build_sheet_produces_png(pngs, tmp_path):
    """Простыню рисует тот же Chrome — сторонняя графика не нужна."""
    import render

    out = contact_sheet.build_sheet(pngs, tmp_path / "contact-sheet.png")
    assert out.exists()
    width, height = render.png_size(out)
    assert width > 1000 and height > 500
    # временный HTML не должен оставаться рядом с результатом
    assert not out.with_suffix(".html").exists()
