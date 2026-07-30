#!/usr/bin/env python3
"""slides.json + тема → самодостаточный HTML одной карточки. Только stdlib.

Самодостаточный значит буквально: шрифты, картинки и стили встроены как
data: URI. Ни одного внешнего запроса и ни одного обращения к file:// из
документа — это снимает и блокировку шрифтов на file://, и зависимость
результата от порядка загрузки.
"""
import argparse
import base64
import json
from pathlib import Path

import markup
import theme as theme_mod

LAYOUTS_DIR = Path(__file__).parent.parent / "layouts"

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".svg": "image/svg+xml",
        ".ttf": "font/ttf", ".otf": "font/otf", ".woff2": "font/woff2"}

CSS_BY_LAYOUT = {"обложка": "cover.css", "тело": "body.css",
                 "тело-список": "body-list.css", "CTA": "cta.css"}

DARK_LAYOUTS = {"обложка", "CTA"}

MEASURE_JS = """
<script>
  window.addEventListener('load', function () {
    var box = document.querySelector('.содержимое');
    if (!box) { return; }
    var over = Math.max(0, box.scrollHeight - box.clientHeight);
    var probe = box.querySelector('*');
    var lh = probe ? parseFloat(getComputedStyle(probe).lineHeight) || 0 : 0;
    document.body.dataset.overflow = String(Math.round(over));
    document.body.dataset.lineHeight = String(Math.round(lh));
  });
</script>
"""


def data_uri(path):
    """Файл → data: URI. Тип берётся по расширению."""
    path = Path(path)
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def font_css(data):
    """@font-face на оба семейства со встроенными файлами."""
    blocks = []
    for family, path in data["шрифты"]["файлы"].items():
        blocks.append(
            "@font-face {\n"
            f"  font-family: '{family.capitalize()}';\n"
            f"  src: url({data_uri(path)}) format('truetype');\n"
            "  font-weight: 200 900;\n"
            "  font-style: normal;\n"
            "}"
        )
    return "\n".join(blocks)


def css_vars(data, sizes):
    """Тема + выбранные кегли → блок :root с переменными."""
    fmt = data["формат"]
    lines = [
        f"--ширина: {fmt['ширина']}px;",
        f"--высота: {fmt['высота']}px;",
        f"--фон-тёмный-1: {data['фоны']['тёмный']['стопы'][0]};",
        f"--фон-тёмный-2: {data['фоны']['тёмный']['стопы'][1]};",
        f"--фон-светлый-1: {data['фоны']['светлый']['стопы'][0]};",
        f"--фон-светлый-2: {data['фоны']['светлый']['стопы'][1]};",
    ]
    for name, value in data["цвета"].items():
        lines.append(f"--{name.replace('_', '-')}: {value};")
    for name, spec in data["шрифты"]["роли"].items():
        lines.append(f"--{name.replace('_', '-')}-вес: {spec['вес']};")
    # Подчёркивания → дефисы, как у цветов и весов: в CSS всё через дефис.
    for name, value in sizes.items():
        lines.append(f"--{name.replace('_', '-')}: {value}px;")
    return ":root {\n  " + "\n  ".join(lines) + "\n}"


def layout_css(layout):
    """base.css + CSS конкретного лейаута."""
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")
    base = (LAYOUTS_DIR / "base.css").read_text(encoding="utf-8")
    own = (LAYOUTS_DIR / CSS_BY_LAYOUT[layout]).read_text(encoding="utf-8")
    return base + "\n" + own


def _badge_html(position):
    if position == "нет":
        return ""
    return (f'<div class="бейдж {position}">ЛИСТАЙ'
            f'<span class="кружок">›</span></div>')


def _signature_html(binding, visible):
    if not visible:
        return ""
    lines = binding["подпись"]
    name = markup.escape(lines[0])
    title = (f'<div class="должность">{markup.escape(lines[1])}</div>'
             if len(lines) > 1 else "")
    return (f'<div class="подпись {binding["подпись_позиция"]}">'
            f'<img src="{data_uri(binding["аватар"])}" alt="">'
            f'<div><div class="имя">{name}</div>{title}</div></div>')


def _cover_body(slide, data, base_dir):
    """Содержимое обложки. Виды: текст (по умолчанию), декор, фото."""
    kind = slide.get("вид", "текст")
    parts = []

    if kind == "фото":
        photo = Path(base_dir) / slide["фото"]
        parts.append(f'<img class="фон" src="{data_uri(photo)}" alt="">')
        parts.append('<div class="затемнение"></div>')
    elif kind == "декор":
        parts.append(f'<img class="спарк" src="{data_uri(data["ассеты"]["спарк"])}" alt="">')

    inner = [f'<div class="заголовок">{markup.inline(slide.get("заголовок", ""))}</div>']
    if slide.get("подзаголовок"):
        inner.append(f'<div class="подзаголовок">{markup.inline(slide["подзаголовок"])}</div>')
    if slide.get("низ"):
        inner.append(f'<div class="низ">{markup.inline(slide["низ"])}</div>')

    parts.append('<div class="содержимое">' + "".join(inner) + "</div>")
    return "".join(parts), kind


def _body_body(slide, data):
    """Абзацы тела. Нить вешается только на последний блок."""
    blocks = slide.get("блоки", [])
    rendered = []
    for i, text in enumerate(blocks):
        html_text = markup.inline(text)
        if slide.get("нить") and i == len(blocks) - 1:
            html_text = markup.with_thread(html_text)
        rendered.append(f'<div class="блок">{html_text}</div>')
    return '<div class="содержимое">' + "".join(rendered) + "</div>"


def _list_body(slide, data):
    """Заголовок → подзаголовок-боль → пункты → подвал курсивом."""
    parts = [f'<div class="заголовок">{markup.inline(slide.get("заголовок", ""))}</div>']
    if slide.get("подзаголовок"):
        parts.append(f'<div class="подзаголовок">{markup.inline(slide["подзаголовок"])}</div>')

    items = "".join(f'<div class="пункт">{markup.inline(x)}</div>'
                    for x in slide.get("пункты", []))
    parts.append(f'<div class="пункты">{items}</div>')

    if slide.get("подвал"):
        parts.append(f'<div class="подвал">{markup.inline(slide["подвал"])}</div>')
    return '<div class="содержимое">' + "".join(parts) + "</div>"


def build(slide, data, platform, sizes, base_dir):
    """Собирает полный HTML-документ одной карточки."""
    layout = slide.get("лейаут")
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")

    binding = theme_mod.binding(data, platform, layout)
    tone = "тёмная" if layout in DARK_LAYOUTS else "светлая"

    if layout == "обложка":
        body, kind = _cover_body(slide, data, base_dir)
        classes = f"карточка {tone} обложка {kind if kind != 'текст' else ''}".strip()
        # На фото-обложке подпись гасится: автор уже на снимке.
        default_visible = kind != "фото"
    elif layout == "тело":
        body = _body_body(slide, data)
        classes = f"карточка {tone} тело"
        default_visible = True
    elif layout == "тело-список":
        body = _list_body(slide, data)
        classes = f"карточка {tone} тело-список"
        default_visible = True
    else:
        raise ValueError(f"лейаут {layout} появится в следующей задаче")

    default = "показать" if default_visible else "скрыть"
    visible = slide.get("подпись", default) == "показать"

    return (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'><style>\n"
        + font_css(data) + "\n" + css_vars(data, sizes) + "\n" + layout_css(layout)
        + "\n</style></head><body>"
        + f'<div class="{classes}">'
        + _badge_html(binding["бейдж"])
        + body
        + _signature_html(binding, visible)
        + "</div>" + MEASURE_JS + "</body></html>"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slides_json")
    ap.add_argument("--theme", required=True)
    ap.add_argument("--slide", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    spec = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
    data = theme_mod.load(args.theme)
    slide = next(s for s in spec["слайды"] if s["№"] == args.slide)
    sizes = {"заголовок": theme_mod.steps(data, "обложка_заголовок")[0],
             "подзаголовок": theme_mod.steps(data, "обложка_подзаголовок")[0]}
    html_text = build(slide, data, spec["meta"]["площадка"], sizes,
                      Path(args.slides_json).parent)
    Path(args.out).write_text(html_text, encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
