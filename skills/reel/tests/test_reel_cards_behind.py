import re

import pytest

import behind
import cards
import words as wmod

# Цвета, которые шаблон вправе держать сам: белые оттенки текста и точки окна терминала.
NEUTRAL = {"#FFFFFF", "#E6E6F2", "#E8E8F5", "#FF5F57", "#FEBC2E", "#28C840"}
OTHER_THEME = {"bg_dark": ["#0A3D0A", "#001100"], "bg_light": ["#FFF0F0", "#FFE0E0"], "text_dark": "#3A0000",
               "secondary": "#AA00AA", "muted": "#557755", "success": "#00AAAA",
               "accent": {"name": "o", "solid": "#FF0055", "on_light": "#990033", "gradient": None}}

SLOTS = {
    "tiles": {"items": [{"icon": "</>", "label": "код", "crossed": True, "at": "Без"},
                        {"icon": "0", "label": "бесплатно", "ok": True, "at": "бесплатно."}]},
    "terminal": {"title": "сервер", "command": "curl -fsSL example.org/install.sh | bash",
                 "type_to": "сервер", "lines": [{"text": "✓ Готово", "at": "работает", "ok": True}]},
    "profile": {"icon": "📣", "title": "Мой канал", "subtitle": "создан", "pill": "✓ Готов", "pill_at": "сам."},
    "chips": {"title": "Источники", "subtitle": "откуда брать", "groups": [
        {"label": "Каналы", "chips": [{"text": "@one", "at": "кода,"}, {"text": "@two"}]},
        {"label": "Ленты", "accent": True, "chips": [{"text": "site/rss"}]}]},
    "rewrite": {"title": "ИИ переписывает", "source_label": "Было", "target_label": "Стало",
                "text": "Свой текст", "badge_at": "редактора"},
    "rows": {"title": "Расписание", "rows": [{"left": "09:00", "right": "✓ готово"},
                                             {"left": "19:00", "right": "◷ ждёт", "state": "wait"}]},
    "compare": {"items": [{"icon": "🖥", "title": "Сервер", "note": "онлайн"},
                          {"icon": "💻", "title": "Ноутбук", "note": "можно выключить", "state": "dim"}]},
    "buttons": {"avatar": "🤖", "title": "Бот", "message": "Работает", "hint": "Что сделать?",
                "buttons": [{"text": "+ Источник", "press_at": "Напиши"}, {"text": "⏸ Пауза"}]},
    "cta": {"lead": "Напиши в комменты", "word": "СЛОВО", "sub": "пришлю ссылку", "sub_at": "пришлю"},
    "sticker": {"text": "🤬", "x": 520, "y": 1100, "size": 170, "rotate": -12},
    "filmstrip": {"text": "СМОНТИРОВАЛ"},
    "logos_cut": {"icons": [], "cut_at": "сам."},
    "thought": {"x": 760, "y": 470, "head": [600, 760], "marks": [{"text": "?", "at": "Без"}, {"text": "!", "at": "бесплатно."}]},
    "chat": {"name": "Клиент", "avatar": "🙂", "msg": "Хочу так же", "msg_from": "Без", "msg_to": "сервер",
             "reply": "Без проблем", "reply_at": "работает"},
    "cc_terminal": {"request": "Разбери, как это сделано", "type_from": "Без", "type_to": "сервер",
                    "lines": [{"text": "Думает…", "kind": "think", "at": "работает"}, {"text": "Готово", "kind": "ok"}]},
}


@pytest.mark.parametrize("tpl", sorted(cards.TEMPLATES))
def test_every_template_builds_seek_safe(tpl, words, theme):
    at = lambda a: wmod.at(words, a)  # noqa: E731
    css, body, js = cards.build([{"template": tpl, "a": 1.0, "b": 6.0, "slots": SLOTS[tpl]}], at, theme)
    assert body and 'data-start="1.000"' in body[0]
    joined = "\n".join(js)
    assert "Math.random" not in joined and "Date.now" not in joined and "tl.call" not in joined
    assert not re.search(r"\b(top|left)\s*:", joined)
    css2, body2, _ = cards.build([{"template": tpl, "a": 1.0, "b": 6.0, "slots": SLOTS[tpl]}], at, OTHER_THEME)
    hexes = lambda t: {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", t)}  # noqa: E731
    shared = hexes(css + body[0]) & hexes(css2 + body2[0])
    assert shared <= NEUTRAL, f"шаблон {tpl} держит цвета мимо темы: {shared - NEUTRAL}"


def test_card_colors_come_from_theme(words, theme):
    theme = dict(theme, accent={"name": "x", "solid": "#123456", "on_light": "#000", "gradient": None})
    css, body, _ = cards.build([{"template": "cta", "a": 0, "b": 2, "slots": SLOTS["cta"]}],
                               lambda a: wmod.at(words, a), theme)
    assert "#123456" in body[0]


def test_unknown_template(words, theme):
    with pytest.raises(ValueError, match="нет шаблона"):
        cards.build([{"template": "nope", "a": 0, "b": 1}], lambda a: 0.0, theme)


def test_card_text_is_escaped(theme):
    _, body, _ = cards.build([{"template": "cta", "a": 0, "b": 1, "slots": {"word": "<b>"}}], lambda a: 0.0, theme)
    assert "&lt;b&gt;" in body[0]


def test_mix():
    assert cards.mix("#000000", "#FFFFFF", 0.5) == "#808080"


BEHIND = [{"from": 0.0, "to": {"word": "Без"}, "phrases": [
    {"lines": [{"size": "l1", "words": [{"text": "Сейчас", "at": 0.0}]},
               {"size": "l2", "words": [{"text": "покажу", "at": "покажу", "color": "secondary"}]}]},
    {"lines": [{"size": "l1", "words": [{"text": "Одна", "at": "одну"}]},
               {"size": "l2", "words": [{"text": "строка", "at": "строку."}]}],
     "strike": {"line": 0, "at": "строку."}}]},
    {"from": {"word": "Напиши", "shift": -0.08}, "to": "end", "subs_from": "пришлю",
     "phrases": [{"lines": [{"size": "huge", "words": [{"text": "СЛОВО", "at": "СЛОВО", "color": "accent"}]}]}]}]


def test_behind_resolve_phrases_chain(words):
    res = behind.resolve(BEHIND, lambda a: wmod.at(words, a), 30.0)
    w1 = res[0]
    assert w1["a"] == 0.0 and w1["b"] == wmod.find(words, "Без")["start"]
    assert w1["phrases"][0]["b"] == round(w1["phrases"][1]["a"] - 0.02, 3)
    assert w1["phrases"][-1]["b"] == w1["b"]
    assert res[1]["b"] == 30.0 and res[1]["subs_from"] == wmod.find(words, "пришлю")["start"]


def test_behind_hidden_and_edges(words):
    res = behind.resolve(BEHIND, lambda a: wmod.at(words, a), 30.0)
    hid = behind.hidden_windows(res)
    assert hid[1][1] == res[1]["subs_from"]
    assert behind.edges(res) == [res[1]["a"]]  # начало ролика краем не считается


def test_behind_build(words, theme):
    res = behind.resolve(BEHIND, lambda a: wmod.at(words, a), 30.0)
    css, body, js, windows = behind.build(res, theme)
    assert windows == [[w["a"], w["b"]] for w in res]
    assert any('class="strike"' in b for b in body)
    assert any('class="w secondary"' in b for b in body)
    assert any("scaleX: 0" in j for j in js)


def test_behind_plate_fades_in_when_asked(words, theme):
    import words as wmod
    at = lambda a: wmod.at(words, a)  # noqa: E731
    res = behind.resolve([{"from": "Сервер", "to": "end", "fade_in": 0.35,
                           "phrases": [{"lines": [{"size": "huge", "words": [{"text": "X", "at": "Сервер"}]}]}]}],
                         at, 30.0)
    _, _, js, _ = behind.build(res, theme)
    assert any('tl.fromTo("#plate1", {opacity: 0}' in j and "duration: 0.35" in j for j in js)


def test_behind_line_top_override(words, theme):
    import words as wmod
    at = lambda a: wmod.at(words, a)  # noqa: E731
    res = behind.resolve([{"from": "Сервер", "to": "end", "phrases": [
        {"lines": [{"size": "huge", "top": 590, "words": [{"text": "X", "at": "Сервер"}]}]}]}], at, 30.0)
    _, body, _, _ = behind.build(res, theme)
    assert any('class="hero huge" style="top:590px"' in b for b in body)


def test_behind_typed_line_and_clamp_to_cut(words, theme):
    at = lambda a: wmod.at(words, a)  # noqa: E731
    res = behind.resolve([{"from": "Сервер", "to": "end", "phrases": [{"lines": [
        {"size": "l1", "type": 0.5, "words": [{"text": "АБВ", "at": "Сервер"}]},
        {"size": "huge", "words": [{"text": "X", "at": "сам."}]}]}]}], at, 30.0)
    behind.clamp_to_spans(res, [(0.0, 3.0), (3.0, 10.0), (10.0, 30.0)])
    assert res[0]["b"] == 9.97 and res[0]["phrases"][-1]["b"] == 9.97
    _, body, js, _ = behind.build(res, theme)
    assert '<span class="ch">А</span><span class="ch">Б</span>' in "\n".join(body)
    assert any(".ch\", {opacity: 0}" in j and "stagger: 0.1667" in j for j in js)


def test_logos_cut_copies_icon_files(tmp_path, words, theme):
    at = lambda a: wmod.at(words, a)  # noqa: E731
    ico = tmp_path / "a.png"
    ico.write_bytes(b"\x89PNG\r\n\x1a\n")
    files = []
    _, body, js = cards.build([{"template": "logos_cut", "a": 1.0, "b": 3.0,
                                "slots": {"icons": [str(ico)], "cut_at": "сам."}}], at, theme, files=files)
    assert files == [(str(ico), "c1-0.png")] and 'src="c1-0.png"' in body[0]
    assert any("scaleX: 1" in j for j in js)
