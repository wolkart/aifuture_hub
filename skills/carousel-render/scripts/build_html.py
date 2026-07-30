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
import re
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

# Какие кегли обязан получить каждый лейаут. Отсутствие ключа — не мелочь:
# CSS с неопределённым var() тихо падает на дефолтные 16px, и карточка
# выглядит «сломанной вёрсткой», а не ошибкой. Поэтому проверяем явно.
SIZE_KEYS = {
    "обложка": ("заголовок", "подзаголовок"),
    "тело": ("тело",),
    "тело-список": ("тело_список",),
    "CTA": ("cta",),
}


def required_sizes(slide):
    """Какие кегли обязательны именно для этого слайда.

    У обложки подзаголовочный кегль нужен только если есть что им набрать:
    подзаголовок, нижняя строка или фото-вид (там им набран сам заголовок).
    """
    layout = slide.get("лейаут")
    if layout != "обложка":
        return SIZE_KEYS[layout]
    keys = ["заголовок"]
    if slide.get("подзаголовок") or slide.get("низ") or slide.get("вид") == "фото":
        keys.append("подзаголовок")
    return tuple(keys)

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
    document.body.dataset.contentHeight = String(Math.round(box.clientHeight));
  });
</script>
"""


def data_uri(path):
    """Файл → data: URI. Тип берётся по расширению."""
    path = Path(path)
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def inline_svg(path, css_class):
    """SVG прямо в разметку, а не через <img>.

    Через `<img src="data:...svg">` SVG остаётся отдельным документом, и
    `currentColor` внутри него не наследует цвет страницы — значок выходит
    чёрным. Вставленный в разметку он перекрашивается из темы.
    """
    markup_text = Path(path).read_text(encoding="utf-8").strip()
    # Убираем XML-пролог и <title>: в inline-SVG они лишние.
    markup_text = re.sub(r"<\?xml.*?\?>", "", markup_text, flags=re.DOTALL)
    markup_text = re.sub(r"<title>.*?</title>", "", markup_text, flags=re.DOTALL)
    return f'<div class="{css_class}">{markup_text.strip()}</div>'


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
    # Тонкая типографика: значения без единиц (em, множитель) — как есть.
    # Необязательный блок, у CSS на каждый ключ свой дефолт.
    for name, value in data.get("типографика", {}).items():
        lines.append(f"--{name.replace('_', '-')}: {value};")
    return ":root {\n  " + "\n  ".join(lines) + "\n}"


def layout_css(layout):
    """base.css + CSS конкретного лейаута."""
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")
    base = (LAYOUTS_DIR / "base.css").read_text(encoding="utf-8")
    own = (LAYOUTS_DIR / CSS_BY_LAYOUT[layout]).read_text(encoding="utf-8")
    return base + "\n" + own


def band_classes(binding, signature_visible):
    """Классы занятости краёв карточки.

    Полоса под обвязку резервируется паддингом. Если на краю никого нет,
    держать её незачем — содержимое получит эту высоту.
    """
    badge, sign = binding["бейдж"], binding["подпись_позиция"]
    if not signature_visible:
        sign = "нет"
    top_busy = "верх-центр" in (badge, sign)
    bottom_busy = badge.startswith("низ") or sign.startswith("низ")
    return " ".join([
        "верх-занят" if top_busy else "верх-свободен",
        "низ-занят" if bottom_busy else "низ-свободен",
    ])


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
        spark = Path(data["ассеты"]["спарк"])
        if spark.suffix.lower() == ".svg":
            parts.append(inline_svg(spark, "спарк"))
        else:
            parts.append(f'<img class="спарк" src="{data_uri(spark)}" alt="">')

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


def _cta_body(slide, data):
    """Текст призыва. Подпись рисуется отдельно, обвязкой."""
    blocks = "".join(f'<div class="блок">{markup.inline(x)}</div>'
                     for x in slide.get("блоки", []))
    return '<div class="содержимое">' + blocks + "</div>"


def build(slide, data, platform, sizes, base_dir):
    """Собирает полный HTML-документ одной карточки."""
    layout = slide.get("лейаут")
    if layout not in CSS_BY_LAYOUT:
        raise ValueError(f"неизвестный лейаут: {layout}")

    missing = [k for k in required_sizes(slide) if k not in sizes]
    if missing:
        raise ValueError(f"лейаут {layout}: не переданы кегли {', '.join(missing)} — "
                         f"без них CSS молча свалится на 16px")

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
    elif layout == "CTA":
        body = _cta_body(slide, data)
        classes = f"карточка {tone} CTA"
        default_visible = True
    else:
        raise ValueError(f"неизвестный лейаут: {layout}")

    default = "показать" if default_visible else "скрыть"
    visible = slide.get("подпись", default) == "показать"
    classes = f"{classes} {band_classes(binding, visible)}"

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
    # Первая (самая крупная) ступень под лейаут слайда. Подбор ступени по
    # объёму текста — работа fit.py, тут только отладочный прогон.
    step_key = {"заголовок": "обложка_заголовок", "подзаголовок": "обложка_подзаголовок",
                "тело": "тело", "тело_список": "тело_список", "cta": "cta"}
    sizes = {name: theme_mod.steps(data, step_key[name])[0]
             for name in SIZE_KEYS[slide["лейаут"]]}
    html_text = build(slide, data, spec["meta"]["площадка"], sizes,
                      Path(args.slides_json).parent)
    Path(args.out).write_text(html_text, encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
