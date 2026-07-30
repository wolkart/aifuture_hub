import pytest

import render


def test_chrome_cmd_screenshot_has_scale_and_size(tmp_path):
    cmd = render.chrome_cmd(tmp_path / "s.html", "screenshot", 1080, 1350, 2,
                            tmp_path / "s.png")
    joined = " ".join(cmd)
    assert "--headless" in joined
    assert "--window-size=1080,1350" in joined
    assert "--force-device-scale-factor=2" in joined
    assert "--screenshot=" in joined


def test_chrome_cmd_always_waits_for_fonts(tmp_path):
    """Без virtual-time-budget скриншот снимается до применения @font-face."""
    for mode in ("screenshot", "dom"):
        cmd = render.chrome_cmd(tmp_path / "s.html", mode, 1080, 1350, 1, None)
        assert any(a.startswith("--virtual-time-budget=") for a in cmd)


def test_chrome_cmd_dom_mode_dumps_and_scales_one(tmp_path):
    """Замер идёт в 1×: он нужен для чисел, а не для картинки."""
    cmd = render.chrome_cmd(tmp_path / "s.html", "dom", 1080, 1350, 1, None)
    assert "--dump-dom" in cmd
    assert "--force-device-scale-factor=1" in " ".join(cmd)


def test_chrome_cmd_uses_file_url(tmp_path):
    html = tmp_path / "s.html"
    cmd = render.chrome_cmd(html, "dom", 1080, 1350, 1, None)
    assert cmd[-1].startswith("file:///")
    assert "s.html" in cmd[-1]


def test_parse_overflow_reads_dataset():
    dom = '<html><body data-overflow="42" data-line-height="70">x</body></html>'
    assert render.parse_overflow(dom) == {"overflow_px": 42, "line_height_px": 70}


def test_parse_overflow_defaults_to_zero():
    assert render.parse_overflow("<html><body>нет данных</body></html>") == {
        "overflow_px": 0, "line_height_px": 0}


def test_parse_overflow_survives_attribute_order():
    dom = '<body data-line-height="55" class="x" data-overflow="7">'
    assert render.parse_overflow(dom)["overflow_px"] == 7


@pytest.mark.integration
def test_screenshot_produces_exact_size(tmp_path):
    """Живой прогон Chrome: размер должен быть ровно 1080×1350."""
    html = tmp_path / "s.html"
    html.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;width:1080px;height:1350px;background:#222147}"
        "</style></head><body><div class='содержимое'>тест</div></body></html>",
        encoding="utf-8")
    png = render.screenshot(html, tmp_path / "s.png", 1080, 1350, 2)
    assert png.exists()
    assert render.png_size(png) == (2160, 2700)
    render.downscale(png, 1080, 1350)
    assert render.png_size(png) == (1080, 1350)


@pytest.mark.integration
def test_measure_reads_overflow_from_live_page(tmp_path):
    """Страница сама считает переполнение — проверяем, что число доезжает."""
    html = tmp_path / "over.html"
    html.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;width:1080px;height:1350px}"
        ".содержимое{height:1350px;overflow:hidden}"
        ".x{height:2000px;line-height:70px}"
        "</style></head><body><div class='содержимое'><div class='x'>текст</div></div>"
        "<script>window.addEventListener('load',function(){"
        "var b=document.querySelector('.содержимое');"
        "document.body.dataset.overflow=String(Math.max(0,b.scrollHeight-b.clientHeight));"
        "document.body.dataset.lineHeight='70';});</script></body></html>",
        encoding="utf-8")
    got = render.measure(html, 1080, 1350)
    assert got["overflow_px"] > 0
    assert got["line_height_px"] == 70
