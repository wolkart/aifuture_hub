from conftest import write
from cards import END, START, update_cards


def card(vault, proj):
    return (vault / "projects" / proj / f"{proj}.md").read_text(encoding="utf-8")


def test_cards_groups(vault):
    assert update_cards(vault) == {"Бот": 0, "Сайт студии": 2}
    text = card(vault, "Сайт студии")
    section = text[text.index(START):text.index(END)]
    assert "**В корне проекта:** [[План]]" in section
    assert "**Дизайн:** [[Макет]]" in section
    assert section.index("В корне проекта") < section.index("Дизайн")
    assert "[[Сайт студии]]" not in section


def test_cards_idempotent(vault):
    update_cards(vault)
    first = card(vault, "Сайт студии")
    update_cards(vault)
    assert card(vault, "Сайт студии") == first


def test_cards_keeps_text(vault):
    before = card(vault, "Сайт студии")
    update_cards(vault)
    after = card(vault, "Сайт студии")
    assert before[:before.index(START)] == after[:after.index(START)]
    p = vault / "projects" / "Бот" / "Бот.md"
    p.write_text("# Бот\n\nтекст без меток\n", encoding="utf-8")
    update_cards(vault)
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# Бот\n\nтекст без меток\n") and text.rstrip().endswith(END)


def test_cards_empty_project(vault):
    update_cards(vault)
    assert "Пока только карточка" in card(vault, "Бот")


def test_cards_same_name(vault):
    write(vault, "projects/Бот/План.md", "# План бота\n")
    update_cards(vault)
    assert "[[projects/Бот/План|План (Бот)]]" in card(vault, "Бот")
    assert "[[projects/Сайт студии/План|План (Сайт студии)]]" in card(vault, "Сайт студии")


def test_cards_no_projects_dir(tmp_path):
    assert update_cards(tmp_path) == {}
