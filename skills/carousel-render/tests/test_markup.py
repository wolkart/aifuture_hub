import markup


def test_escape_kills_tags():
    assert markup.escape("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;"


def test_escape_handles_ampersand():
    assert markup.escape("Тим & Ко") == "Тим &amp; Ко"


def test_inline_wraps_accent():
    assert markup.inline("код и **замолчит**.") == 'код и <b class="акцент">замолчит</b>.'


def test_inline_handles_several_accents():
    got = markup.inline("У **Claude** есть **ADHD**")
    assert got == 'У <b class="акцент">Claude</b> есть <b class="акцент">ADHD</b>'


def test_inline_is_non_greedy():
    """Два отдельных выделения, а не одно на всю строку.

    Жадный маркер съел бы «между» внутрь одного <b> — проверяем, что текст
    между выделениями остался снаружи.
    """
    got = markup.inline("**раз** между **два**")
    assert got == ('<b class="акцент">раз</b> между '
                   '<b class="акцент">два</b>')


def test_inline_newline_becomes_br():
    assert markup.inline("Агент.\nХарнес.") == "Агент.<br>Харнес."


def test_inline_escapes_before_markup():
    """Текст пользователя не должен протаскивать разметку."""
    got = markup.inline("**<b>злой</b>**")
    assert got == '<b class="акцент">&lt;b&gt;злой&lt;/b&gt;</b>'


def test_inline_leaves_lone_asterisks():
    assert markup.inline("5 * 3 = 15") == "5 * 3 = 15"


def test_inline_leaves_unclosed_marker():
    assert markup.inline("**не закрыл") == "**не закрыл"


def test_with_thread_appends_arrow():
    got = markup.with_thread("Первая её часть")
    assert got.endswith(markup.ARROW)
    assert "Первая её часть" in got


def test_arrow_is_element_not_character():
    """Стрелка — элемент со своим классом, иначе её не стилизовать."""
    assert 'class="нить"' in markup.ARROW
