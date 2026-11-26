import unicodedata

from conftest import write
from links import broken_links


def test_template_vault_clean(vault):
    assert broken_links(vault) == set()


def test_broken_links_found(vault):
    write(vault, "wiki/Заметка.md", "см. [[Нет такой]]\n")
    assert ("wiki/Заметка.md", "Нет такой") in broken_links(vault)


def test_link_forms(vault):
    write(vault, "files/картинка.png", "")
    write(vault, "wiki/Ссылки.md",
          "[[План]] [[План|текст]] [[projects/Сайт студии/План]] ![[картинка.png]] [[План#раздел]]\n")
    assert not [b for b in broken_links(vault) if b[0] == "wiki/Ссылки.md"]


def test_nfd_name(vault):
    write(vault, "wiki/" + unicodedata.normalize("NFD", "Йога") + ".md", "# Йога\n")
    write(vault, "wiki/Спорт.md", "[[Йога]]\n")
    assert broken_links(vault) == set()


def test_ignores_code(vault):
    write(vault, "wiki/Код.md", "Ссылки `[[нет1]]` пишутся так.\n\n```\n[[нет2]]\n```\n")
    assert broken_links(vault) == set()


def test_cards_dir_skipped(vault):
    write(vault, "raw/выгрузка/cards/1.md", "[[нет]]\n")
    assert broken_links(vault) == set()
