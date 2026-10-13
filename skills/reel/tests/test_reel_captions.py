import captions as cap
from conftest import make_words


def test_hidden_window_splits_segments(words):
    segs = cap.visible_segments(words, hidden=[(0.0, 1.0)])
    assert all(w["start"] >= 1.0 for s in segs for w in s)
    assert sum(len(s) for s in segs) == sum(1 for w in words if w["start"] >= 1.0)


def test_line_pages_respect_width_and_two_lines(words):
    pages = cap.line_pages(cap.visible_segments(words), dur=30.0)
    for pg in pages:
        assert 1 <= len(pg["lines"]) <= 2
        for ln in pg["lines"]:
            text = " ".join(w["text"] for w in ln)
            assert len(text) <= cap.MAXC or len(ln) == 1


def test_line_page_ends_on_sentence_and_holds_until_next(words):
    pages = cap.line_pages(cap.visible_segments(words), dur=30.0)
    first_sentence_end = next(i for i, p in enumerate(pages) if p["ws"][-1]["text"].endswith("."))
    assert pages[first_sentence_end + 1]["ws"][0]["text"] == "Без"
    for a, b in zip(pages, pages[1:]):
        assert a["b"] <= b["a"] + 1e-6
    assert pages[-1]["b"] <= 30.0


def test_edge_cuts_page_before_behind_text():
    ws = make_words("раз два три четыре пять шесть")
    pages = cap.line_pages([ws], dur=10.0, edges=[ws[-1]["end"] + 0.1])
    assert pages[-1]["b"] < ws[-1]["end"] + 0.1


def test_word_beats_glue_service_words(words):
    beats = cap.word_beats(cap.visible_segments(words), dur=30.0)
    texts = [" ".join(w["text"] for w in b["ws"]) for b in beats]
    assert "и бесплатно." in texts and "в комменты," in texts
    assert "Без" in texts  # «без» не служебное: держится отдельным ударом
    assert all(len(b["ws"]) <= 2 for b in beats)


def test_font_px_shrinks_long_words():
    assert cap.font_px("канал", 72) == 72
    assert cap.font_px("автоматизацию", 72) < 72


def test_render_words_accent_only_on_accent_words(words, opts, theme):
    opts = dict(opts, style="word")
    theme = dict(theme, accent={"name": "x", "solid": "#ABCDEF", "on_light": "#000", "gradient": None})
    beats = cap.word_beats(cap.visible_segments(words), 30.0)
    css, body, js = cap.render_words(beats, opts, theme, accent_words=["бесплатно"])
    marked = [b for b in body if "#ABCDEF" in b]
    assert len(marked) == 1 and ">б<" in marked[0]
    assert all("tl.fromTo" in j for j in js)


def test_render_words_gradient_and_half_lift(words, opts, theme):
    opts = dict(opts, style="word")
    theme = dict(theme, accent={"name": "g", "solid": "#00FF00", "on_light": "#000", "gradient": ["#00FFFF", "#00FF00"]})
    beats = cap.word_beats(cap.visible_segments(words), 30.0)
    _, body, _ = cap.render_words(beats, opts, theme, ["сервер"], half_windows=[(0.0, 1.5)])
    assert any("linear-gradient(90deg,#00FFFF,#00FF00)" in b for b in body)
    assert f'top:{opts["top_half_px"] + 20}px' in body[0]
    assert f'top:{opts["top_px"]}px' in body[-1]


def test_anim_variants(words, opts, theme):
    beats = cap.word_beats(cap.visible_segments(words), 30.0)
    for anim, marker in (("pop", "scale: 0.8"), ("wave", "yPercent: 115")):
        _, _, js = cap.render_words(beats, dict(opts, anim=anim), theme)
        assert marker in js[0]
    _, _, js = cap.render_words(beats, dict(opts, anim="none"), theme)
    assert js == []


def test_render_lines_karaoke(words, opts, theme):
    pages = cap.line_pages(cap.visible_segments(words), 30.0)
    css, body, js = cap.render_lines(pages, opts, theme)
    n_words = sum(len(p["ws"]) for p in pages)
    assert sum(1 for j in js if "tl.set(" in j) == 2 * n_words
    assert len(body) == len(pages)


def test_build_switches_style(words, opts, theme):
    *_, units = cap.build(words, 30.0, dict(opts, style="word"), theme)
    assert all(len(u["lines"]) == 1 for u in units)
    *_, units = cap.build(words, 30.0, dict(opts, style="lines"), theme)
    assert cap.summary(units)[0].strip().startswith("0.14")
