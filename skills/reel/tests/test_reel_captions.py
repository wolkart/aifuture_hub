import pytest
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


# ── ключи по ходу ролика: место и стиль меняются на слове ────────────────────

def test_keys_switch_style_and_slide_under_gesture(words, opts, theme):
    keys = [{"t": 0.0, "top": 900}, {"t": 0.9, "top": 1385, "slide": 0.5},
            {"t": 3.0, "style": "caps"}, {"t": 6.0, "style": "word"}]
    css, body, js, units = cap.build(words, 30.0, dict(opts, style="lines"), theme, keys=keys)
    html = "\n".join(body)
    assert 'class="rail" style="top:900px"' in html            # сначала на лице
    assert 'class="cap"' in html and 'class="wcap"' in html    # капс, потом по слову
    assert ".cap {" in css and ".wcap {" in css and ".rail {" in css
    assert any("y: 485" in j and "immediateRender: false" in j for j in js)   # строка едет вниз, не прыгает
    ids = [b.split('"')[1] for b in body]
    assert len(ids) == len(set(ids)) and all(i.startswith("c") for i in ids)
    caps_units = [u for u in units if 3.0 <= u["a"] < 6.0]
    assert caps_units and all(len(u["ws"]) <= cap.CAPS_WORDS for u in caps_units)


def test_style_change_cuts_unit_at_boundary(words, opts, theme):
    parts, _ = cap.keyed_units(words, 30.0, dict(opts, style="lines"), keys=[{"t": 1.0, "style": "word"}])
    assert [p["style"] for p in parts] == ["lines", "word"]
    assert all(u["b"] <= 1.0 for u in parts[0]["units"])


def test_without_keys_old_ids_and_one_style(words, opts, theme):
    _, body, _, _ = cap.build(words, 30.0, dict(opts, style="word"), theme)
    assert body[0].startswith('<div id="r0"')


def test_caps_pages_three_words_max():
    ws = make_words("один два три четыре пять шесть семь")
    pages = cap.caps_pages([ws], 10.0)
    assert sum(len(p["ws"]) for p in pages) == 7
    for p in pages:
        text = " ".join(w["text"] for w in p["ws"])
        assert len(p["ws"]) <= cap.CAPS_WORDS and (len(text) <= cap.CAPS_MAXC or len(p["ws"]) == 1)
    assert all(a["b"] <= b["a"] + 1e-6 for a, b in zip(pages, pages[1:]))


def test_plan_keys_resolve_names_hidden_and_errors(words):
    import words as wmod
    at = lambda a: wmod.at(words, a)  # noqa: E731
    plan = {"captions_from": "одну", "captions_hide": [{"from": "Напиши", "to": "end"}],
            "captions_keys": [{"at": "Без", "style": "капс"}, {"at": "Сервер", "top": 1300, "slide": 0.4}]}
    hidden, keys = cap.plan_keys(plan, at, 30.0)
    assert hidden[0][0] == 0.0 and hidden[-1][1] > 30.0
    assert keys[0]["style"] == "caps" and keys[1]["top"] == 1300 and keys[1]["slide"] == 0.4
    with pytest.raises(ValueError):
        cap.plan_keys({"captions_keys": [{"at": "Без", "style": "мигающий"}]}, at, 30.0)


def test_fire_markup_and_replace(words, opts, theme):
    assert cap.fire("АХУ***[[!]]") == 'АХУ***<span class="fire">!</span>'
    assert cap.fire("<b>[[x]]") == '&lt;b&gt;<span class="fire">x</span>'
    shown = cap.replace_words(words, {"Без": "БЕЗ[[!]]"})
    css, body, _, _ = cap.build(shown, 30.0, dict(opts, style="lines"), theme,
                                keys=[{"t": 0.0, "style": "caps", "px": 150}])
    assert '<span class="fire">!</span>' in "\n".join(body) and ".fire {" in css
    assert "--cpx:150px" in "\n".join(body)


def test_style_key_enter_from_edge(words, opts, theme):
    _, _, js, _ = cap.build(words, 30.0, dict(opts, style="lines"), theme,
                            keys=[{"t": 1.0, "style": "caps", "enter": "right"}])
    assert any("x: 1150" in j and ".cap" in j for j in js)


def test_title_style_stacked_and_fits_width(opts, theme):
    ws = make_words("Этот ролик полностью СМОНТИРОВАЛ. ИИ, я вообще")
    css, body, _, units = cap.build(ws, 30.0, dict(opts, style="lines"), theme,
                                    keys=[{"t": 0.0, "style": "title", "px": 150}])
    html = "\n".join(body)
    assert '<span class="l1">Этот ролик</span>' in html and ">полностью<" in html
    assert cap.title_px("СМОНТИРОВАЛ") * 0.68 * 11 <= cap.TITLE_W + 1      # не уходит за край
    assert "text-shadow: 0 0 4px" not in css.split(".tt")[1] and "stroke" not in css


def test_inserted_caption_words_start_own_unit(words, opts, theme):
    ins = cap.insert_words(words, [{"t": 3.05, "text": "новый стиль", "dur": 0.4}])
    assert any(w.get("inserted") and w["text"] == "новый стиль" for w in ins)
    assert [w["start"] for w in ins] == sorted(w["start"] for w in ins)


def test_unit_ends_where_hidden_window_starts(opts, theme):
    ws = make_words("Этот ролик полностью смонтировал сам", gap=0)
    hide = (ws[3]["start"] - 0.02, ws[3]["end"])
    _, _, _, units = cap.build(ws, 30.0, dict(opts, style="lines"), theme, hidden=[hide],
                               keys=[{"t": 0.0, "style": "title"}])
    first = units[0]
    assert first["b"] <= hide[0] + 1e-6


def test_title_page_breaks_after_fire_word_and_spaces_kept(words, opts, theme):
    ws = make_words("Аху... Ты просто")
    shown = cap.replace_words(ws, {"Аху...": "[[АХУ***!]]"})
    pages = cap.title_pages([shown], 10.0)
    assert [len(p["ws"]) for p in pages][0] == 1
    _, body, _, _ = cap.build(cap.insert_words(words, [{"t": 3.05, "text": "новый стиль"}]), 30.0,
                              dict(opts, style="word"), theme)
    assert "&nbsp;" in "\n".join(body)


def test_key_style_top_follows_part_not_lead_in(opts, theme):
    """Слово показывается чуть раньше, чем звучит: первое крупное слово — на высоте заголовка (а не
    старого стиля), первое обычное после него — на своей высоте, а не наверху (баг 2026-10-17)."""
    ws = make_words("раз два внутрь программы даже если")
    k_in, k_out = ws[2]["start"], ws[4]["start"]     # ключ ровно на слове; показ слова — раньше ключа
    keys = [{"t": k_in, "style": "title"}, {"t": k_out, "style": "word"}]
    _, body, _, units = cap.build(ws, 10.0, dict(opts, style="word", top_px=1450), theme, keys=keys)
    import re
    text = lambda b: re.sub(r"<[^>]+>|\\s", "", b)  # noqa: E731  (по_слову бьёт слово на буквы)
    title_div = next(b for b in body if "внутрь" in text(b))
    after_div = next(b for b in body if "даже" in text(b))
    assert f"top:{cap.STYLE_TOP['title']}px" in title_div, title_div[:200]
    assert "top:1450px" in after_div, after_div[:200]
