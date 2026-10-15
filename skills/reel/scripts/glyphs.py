"""Проверка шрифта до рендера: есть ли в нём каждая буква из текста слоя. Только stdlib.

Зачем: если в шрифте темы нет буквы («ё», «Ж», «₽»), Chrome молча нарисует её
другим шрифтом — в кадре выйдет слово из двух шрифтов, а заметно это только
глазами на готовом ролике. Проверка — по таблице символов (cmap) файла шрифта,
до рендера, за миллисекунды.

Какой текст каким шрифтом: элемент рисуется крупным шрифтом (var(--display)),
если на нём или на предке стоит inline-стиль с var(--display) или класс/id из
CSS-правила с font-family: var(--display); остальное — основным.
Буквы и цифры обязаны быть в шрифте (✗); прочие символы (₽, ✓, →, эмодзи)
только перечисляются: их фолбэк обычно и задуман.

Поддержаны TTF/OTF/TTC (cmap форматов 4 и 12). WOFF не разбирается — проверка
для него пропускается с пометкой.
"""
import html
import re
import struct
import unicodedata
from html.parser import HTMLParser
from pathlib import Path


def font_codepoints(path):
    """Множество кодов символов в шрифте; None — формат не разобрать."""
    data = Path(path).read_bytes()
    off = 0
    if data[:4] == b"ttcf":
        off = struct.unpack(">I", data[12:16])[0]
    if data[off:off + 4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        return None
    num = struct.unpack(">H", data[off + 4:off + 6])[0]
    cmap = None
    for i in range(num):
        rec = off + 12 + 16 * i
        if data[rec:rec + 4] == b"cmap":
            cmap = struct.unpack(">I", data[rec + 8:rec + 12])[0]
    if cmap is None:
        return None
    out = set()
    n_sub = struct.unpack(">H", data[cmap + 2:cmap + 4])[0]
    for i in range(n_sub):
        pid, eid, sub = struct.unpack(">HHI", data[cmap + 4 + 8 * i:cmap + 12 + 8 * i])
        if (pid, eid) not in ((0, 3), (0, 4), (0, 6), (3, 1), (3, 10)):
            continue
        base = cmap + sub
        fmt = struct.unpack(">H", data[base:base + 2])[0]
        if fmt == 4:
            out |= _format4(data, base)
        elif fmt == 12:
            out |= _format12(data, base)
    return out


def _format4(data, base):
    seg2 = struct.unpack(">H", data[base + 6:base + 8])[0]
    ends = base + 14
    starts = ends + seg2 + 2
    deltas = starts + seg2
    ranges = deltas + seg2
    out = set()
    for k in range(seg2 // 2):
        end, start = (struct.unpack(">H", data[a + 2 * k:a + 2 * k + 2])[0] for a in (ends, starts))
        delta = struct.unpack(">h", data[deltas + 2 * k:deltas + 2 * k + 2])[0]
        ro_pos = ranges + 2 * k
        ro = struct.unpack(">H", data[ro_pos:ro_pos + 2])[0]
        for c in range(start, end + 1):
            if c == 0xFFFF:
                continue
            if ro == 0:
                g = (c + delta) & 0xFFFF
            else:
                at = ro_pos + ro + 2 * (c - start)
                g = struct.unpack(">H", data[at:at + 2])[0]
                g = (g + delta) & 0xFFFF if g else 0
            if g:
                out.add(c)
    return out


def _format12(data, base):
    n = struct.unpack(">I", data[base + 12:base + 16])[0]
    out = set()
    for k in range(n):
        s, e, _g = struct.unpack(">III", data[base + 16 + 12 * k:base + 28 + 12 * k])
        out |= set(range(s, e + 1))
    return out


def display_markers(css):
    """Классы и id из CSS-правил с font-family: var(--display) — последний простой
    селектор каждого правила («.tile .ic» → класс ic, «#lbl» → id lbl)."""
    classes, ids = set(), set()
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "var(--display)" not in body:
            continue
        for part in sel.split(","):
            last = part.strip().split()[-1] if part.strip() else ""
            for kind, name in re.findall(r"([.#])([\w-]+)", last):
                (classes if kind == "." else ids).add(name)
    return classes, ids


class _Texts(HTMLParser):
    VOID = {"br", "img", "meta", "link", "input", "hr", "source", "i"}

    def __init__(self, classes, ids):
        super().__init__(convert_charrefs=True)
        self.classes, self.ids = classes, ids
        self.stack, self.skip, self.out = [], 0, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
            return
        own = ("var(--display)" in (a.get("style") or "")
               or bool(set((a.get("class") or "").split()) & self.classes)
               or (a.get("id") or "") in self.ids)
        if tag not in self.VOID:
            self.stack.append(own or (self.stack[-1] if self.stack else False))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, text):
        if not self.skip and text.strip():
            self.out.append((self.stack[-1] if self.stack else False, text))


def texts(page_html):
    """Страница слоя → (текст основным шрифтом, текст крупным шрифтом)."""
    css = "".join(re.findall(r"<style>(.*?)</style>", page_html, re.S))
    p = _Texts(*display_markers(css))
    p.feed(page_html)
    main = "".join(t for d, t in p.out if not d)
    display = "".join(t for d, t in p.out if d)
    return html.unescape(main), html.unescape(display)


def strict(ch):
    return unicodedata.category(ch)[0] in "LN"


def check(page_html, font_main, font_display):
    """→ {"missing": [(шрифт, символы)], "soft": [(шрифт, символы)], "skipped": [шрифт]}"""
    res = {"missing": [], "soft": [], "skipped": []}
    for text, font in zip(texts(page_html), (font_main, font_display)):
        if not font or not text.strip():
            continue
        cps = font_codepoints(font)
        if cps is None:
            res["skipped"].append(Path(font).name)
            continue
        chars = sorted({c for c in text if not c.isspace() and ord(c) not in cps})
        hard = "".join(c for c in chars if strict(c))
        soft = "".join(c for c in chars if not strict(c))
        if hard:
            res["missing"].append((Path(font).name, hard))
        if soft:
            res["soft"].append((Path(font).name, soft))
    return res


def report(res, where):
    """Строки отчёта; первая — ✗, если буквы рисуются чужим шрифтом."""
    lines = [f"✗ {where}: в шрифте {name} нет «{' '.join(chars)}» — Chrome нарисует их другим шрифтом"
             for name, chars in res["missing"]]
    lines += [f"  {where}: символы из системного шрифта ({name}): {' '.join(chars)}" for name, chars in res["soft"]]
    lines += [f"  {where}: шрифт {name} не проверен (не TTF/OTF)" for name in res["skipped"]]
    return lines
