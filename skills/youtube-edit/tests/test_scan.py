"""Детекторы скана на синтетических кадрах (без ffmpeg)."""
import numpy as np

import scan

GH, GW, FPS = scan.GH, scan.GW, scan.FPS


def test_runs_merge_and_bounds():
    flags = [0, 1, 1, 0, 1, 1, 1, 0, 0, 0, 1]
    assert scan.runs(flags, 1) == [(1, 3), (4, 7), (10, 11)]
    assert scan.runs(flags, 1, merge_gap=1) == [(1, 7), (10, 11)]
    assert scan.runs(flags, 1, min_len=2, max_len=2) == [(1, 3)]


def test_cell_changes_grid():
    a = np.zeros((GH * scan.CELL, GW * scan.CELL), np.uint8)
    b = a.copy()
    b[:scan.CELL, :scan.CELL] = 200                            # одна клетка в углу
    ch = scan.cell_changes(a, b)
    assert ch.shape == (GH, GW) and ch.sum() == 1 and ch[0, 0]


def synthetic(seconds=40):
    """Экран стоит, кружок камеры (клетки 6–7 × 13–14) шевелится всегда, на 10–10,6 с — зум (весь кадр)."""
    n = seconds * FPS
    ch = np.zeros((n, GH, GW), bool)
    ch[::2, 6:8, 13:15] = True                                  # кружок меняется в половине кадров
    ch[100:106] = True                                          # переход зума 0,6 с
    ch[300:302, 2, 3] = True                                    # курсор моргнул — экран всё равно стоит
    return ch


def test_motion_finds_transition_mask_and_static():
    m = scan.motion(synthetic(), head_spans=[])
    assert m["transitions"] == [(10.0, 10.6)]
    assert m["mask_cells"] == 4                                 # кружок камеры не мешает «висящему экрану»
    assert any(a <= 11 and b >= 39 for a, b in m["static"])


def test_motion_ignores_head_for_transitions():
    m = scan.motion(synthetic(), head_spans=[(9.0, 12.0)])
    assert m["transitions"] == []


def test_head_spans_threshold_and_gaps():
    rows = [(float(t), 0.15 if 5 <= t < 20 and t != 10 else 0.05) for t in range(30)]
    assert scan.head_spans(rows) == [(5.0, 20.0)]               # дыра в 1 с сшита
