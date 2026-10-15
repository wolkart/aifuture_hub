import struct

import glyphs


def sfnt(subtable, platform=(3, 1)):
    """Минимальный TTF: одна таблица cmap с одной подтаблицей."""
    cmap = struct.pack(">HH", 0, 1) + struct.pack(">HHI", platform[0], platform[1], 12) + subtable
    head = b"\x00\x01\x00\x00" + struct.pack(">HHHH", 1, 16, 0, 0)
    rec = b"cmap" + struct.pack(">III", 0, 12 + 16, len(cmap))
    return head + rec + cmap


def fmt4(ranges):
    segs = list(ranges) + [(0xFFFF, 0xFFFF)]
    n = len(segs)
    body = (b"".join(struct.pack(">H", e) for _, e in segs) + b"\x00\x00"
            + b"".join(struct.pack(">H", s) for s, _ in segs)
            + b"".join(struct.pack(">h", 1) for _ in segs)
            + b"".join(struct.pack(">H", 0) for _ in segs))
    return struct.pack(">HHHHHHH", 4, 14 + len(body), 0, 2 * n, 0, 0, 0) + body


def fmt12(ranges):
    groups = b"".join(struct.pack(">III", s, e, 1) for s, e in ranges)
    return struct.pack(">HHIII", 12, 0, 16 + len(groups), 0, len(ranges)) + groups


def font(tmp_path, name, sub, platform=(3, 1)):
    p = tmp_path / name
    p.write_bytes(sfnt(sub, platform))
    return p


LATIN = [(0x20, 0x7E)]
CYR = [(0x0410, 0x044F)]          # А–я без «ё» и «Ё»


def test_format4_and_format12(tmp_path):
    f4 = glyphs.font_codepoints(font(tmp_path, "a.ttf", fmt4(LATIN + CYR)))
    f12 = glyphs.font_codepoints(font(tmp_path, "b.ttf", fmt12(LATIN + CYR + [(0x1F4AC, 0x1F4AC)]), (3, 10)))
    for cps in (f4, f12):
        assert ord("A") in cps and ord("Ж") in cps and ord("ё") not in cps and 0xFFFF not in cps
    assert 0x1F4AC in f12


def test_not_a_font(tmp_path):
    p = tmp_path / "x.woff2"
    p.write_bytes(b"wOF2....")
    assert glyphs.font_codepoints(p) is None


PAGE = """<html><head><style>
.tile .ic { font-family: var(--display); font-size: 96px; }
#lbl { font-family: var(--display); }
.sub { color: #fff; }
</style></head><body>
<div class="tile"><div class="ic">0 ₽</div><div class="tl">ёлка</div></div>
<div id="lbl">ТЕЛЕГА</div>
<div style="font-family:var(--display)">Ёж <span>ok</span></div>
<span class="sub">Привет 💬</span>
<script>const t = "Ъ";</script>
</body></html>"""


def test_texts_split_by_font():
    main, display = glyphs.texts(PAGE)
    assert "ёлка" in main and "Привет" in main and "Ъ" not in main + display
    assert "0 ₽" in display and "ТЕЛЕГА" in display and "Ёж ok" in display


def test_check_strict_letters_and_soft_symbols(tmp_path):
    f = font(tmp_path, "m.ttf", fmt4(LATIN + CYR))
    res = glyphs.check(PAGE, f, f)
    hard = dict(res["missing"])
    assert hard["m.ttf"] in ("ё", "Ё")  # буквы — ошибка, по разу на шрифт
    assert sorted("".join(c for _, c in res["missing"])) == ["Ё", "ё"]
    assert any("💬" in chars for _, chars in res["soft"]) and any("₽" in chars for _, chars in res["soft"])
    lines = glyphs.report(res, "front")
    assert lines[0].startswith("✗ front: в шрифте m.ttf нет")


def test_check_skips_missing_font_and_unknown_format(tmp_path):
    p = tmp_path / "x.woff"
    p.write_bytes(b"wOFF")
    res = glyphs.check(PAGE, None, p)
    assert res["missing"] == [] and res["skipped"] == ["x.woff"]
