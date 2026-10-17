import pytest

import screen_broll as sb


@pytest.mark.parametrize("layout", ["full", "half"])
def test_window_has_no_empty_top_and_fits_canvas(layout):
    x, y, w, h = sb.window_rect(layout)
    cw, ch = sb.CANVAS[layout]
    assert y == sb.MARGIN <= 40                      # над окном нет пустоты (урок 2026-10-17)
    assert x + w <= cw and y + h <= ch


def test_full_window_leaves_room_for_captions():
    _, y, _, h = sb.window_rect("full")
    assert y + h < 1450                              # субтитры (верх_px 1450) — под окном, не на нём


def test_camera_interpolates_and_stays_inside_region():
    keys = [{"t": 0, "cx": 270, "cy": 300, "w": 540}, {"t": 2, "cx": 100, "cy": 900, "w": 300}]
    for t in (0, 0.5, 1, 1.5, 2, 3):
        x, y, w, h = sb.camera_at(keys, t, aspect=0.9, region_w=540, region_h=1000)
        assert 0 <= x and x + w <= 540 + 1e-6 and 0 <= y and y + h <= 1000 + 1e-6
    assert sb.camera_at(keys, 0, 0.9, 540, 1000)[2] == 540
    assert sb.camera_at(keys, 3, 0.9, 540, 1000)[2] == 300


def test_camera_width_never_exceeds_region():
    x, y, w, h = sb.camera_at([{"t": 0, "cx": 270, "cy": 100, "w": 900}], 0, aspect=0.9, region_w=540, region_h=400)
    assert w <= 540 and h <= 400


def test_pop_scale_overshoots_then_settles():
    assert sb.pop_scale(0) == pytest.approx(0.6)
    assert sb.pop_scale(0.7) == pytest.approx(1.08)
    assert sb.pop_scale(1.0) == 1.0


def test_to_window_scales_with_camera():
    cam = (100, 200, 270, 240)                       # окно камеры 270 CSS-px → 1000 px: ×3,7
    bx, by, bw, bh = sb.to_window((100, 200, 27, 10), cam, inner_w=1000)
    assert (bx, by) == (0, 0) and bw == pytest.approx(100) and bh == pytest.approx(1000 / 27)
