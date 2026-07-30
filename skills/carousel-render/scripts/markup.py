#!/usr/bin/env python3
"""Инлайн-разметка текста слайда → HTML. Только stdlib.

Маркер один — `**…**`, а смысл ему подставляет лейаут: в теле это жирное
начертание, на обложке акцентный цвет. Автору не надо помнить, где какой
цвет: он пишет «выделить».
"""
import html
import re

ACCENT_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

# Стрелка-нить рисуется, а не набирается символом. Глиф «⇢» в Montserrat даёт
# залитый треугольник — тяжелее и короче открытой стрелки штрихом, которую
# ставит автор. Вектор в em-единицах масштабируется вместе с кеглем текста.
ARROW_SVG = (
    '<svg viewBox="0 0 46 16" aria-hidden="true">'
    '<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="butt">'
    '<path d="M1 8h6M11 8h6M21 8h9"/>'
    '<path d="M32.5 2 38.5 8l-6 6" stroke-linejoin="miter"/>'
    "</g></svg>"
)
ARROW = f'<span class="нить">{ARROW_SVG}</span>'


def escape(text):
    """HTML-экранирование. Текст автора не должен протаскивать разметку."""
    return html.escape(text, quote=False)


def inline(text):
    """Экранирует, затем разворачивает `**…**` и переводы строк.

    Порядок важен: сначала экранирование, потом наша разметка — иначе
    экранирование съело бы теги, которые мы сами же и поставили.
    """
    safe = escape(text)
    marked = ACCENT_RE.sub(r'<b class="акцент">\1</b>', safe)
    return marked.replace("\n", "<br>")


def with_thread(html_text):
    """Вешает стрелку-нить в конец. Приём «разрез фразы через свайп»."""
    return f"{html_text} {ARROW}"
