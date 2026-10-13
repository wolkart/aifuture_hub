import gaze_trim

FPS = 30
DOWN = 2.0  # «смотрит в сценарий» — наклон больше


def frames(a, b, pitch_fn):
    n = int(round((b - a) * FPS))
    return [(round(a + i / FPS, 3), pitch_fn(a + i / FPS)) for i in range(n)]


def test_start_moves_to_first_look_at_camera():
    # кусок 10.0–14.0, речь 10.6–13.5; до 10.4 смотрит вниз (+8°), потом в камеру (−6°)
    head = frames(10.0, 10.85, lambda t: 8.0 if t < 10.4 else -6.0)
    s, e, notes = gaze_trim.trim_edges(10.0, 14.0, 10.6, 13.5, head, [], DOWN, 0.03)
    assert abs(s - 10.4) < 0.04
    assert e == 14.0
    assert "смотрел в сценарий" in notes[0]


def test_start_never_cuts_into_speech():
    # поднял глаза только после начала речи → начало = речь − guard, плюс пометка
    head = frames(10.0, 10.85, lambda t: 8.0 if t < 10.8 else -6.0)
    s, _, notes = gaze_trim.trim_edges(10.0, 14.0, 10.6, 13.5, head, [], DOWN, 0.03)
    assert abs(s - 10.57) < 0.005
    assert any("не подняв глаза" in n for n in notes)


def test_tail_cut_when_looking_down_after_speech():
    tail = frames(13.5, 14.0, lambda t: -6.0 if t < 13.6 else 9.0)
    _, e, notes = gaze_trim.trim_edges(10.0, 14.0, 10.6, 13.5, [], tail, DOWN, 0.03)
    assert abs(e - 13.6) < 0.04
    assert "ушёл в сценарий" in notes[-1]


def test_no_face_means_no_change():
    head = frames(10.0, 10.85, lambda t: None)
    tail = frames(13.5, 14.0, lambda t: None)
    s, e, notes = gaze_trim.trim_edges(10.0, 14.0, 10.6, 13.5, head, tail, DOWN, 0.03)
    assert (s, e, notes) == (10.0, 14.0, [])


def test_looking_at_camera_from_first_frame_keeps_start():
    head = frames(10.0, 10.85, lambda t: -6.0)
    s, _, notes = gaze_trim.trim_edges(10.0, 14.0, 10.6, 13.5, head, [], DOWN, 0.03)
    assert s == 10.0 and notes == []


def test_speech_bounds_from_energy():
    db_at = lambda t: -20.0 if 1.0 <= t < 2.0 else -90.0
    on, off = gaze_trim.speech_bounds(db_at, 0.5, 2.5, -38.0)
    assert abs(on - 1.0) < 0.011 and abs(off - 2.0) < 0.011
