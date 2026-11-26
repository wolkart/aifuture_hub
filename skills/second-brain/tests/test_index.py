import shutil

from conftest import write
from index import build_index, describe

TODAY = "2026-11-26"
SECTIONS = ["## Обо мне", "## Проекты", "## Знания — wiki/", "## Контент — content/",
            "## Сырьё — raw/ (не править)", "## Дневник — journal/",
            "## Архив — archive/ (история, не переписывать)", "## Шаблоны — templates/"]


def test_sections_order(vault):
    text = build_index(vault, today=TODAY)
    pos = [text.index(s) for s in SECTIONS]
    assert pos == sorted(pos)


def test_project_card_first(vault):
    text = build_index(vault, today=TODAY)
    block = text[text.index("### Сайт студии"):]
    lines = [l for l in block.splitlines()[1:] if l.strip()]
    assert lines[0].startswith("- [[Сайт студии]] — карточка проекта")
    assert "- [[План]] — план сайта" in block
    assert "- **Дизайн/**" in block and "  - [[Макет]]" in block


def test_big_folder_one_line(vault):
    for i in range(31):
        write(vault, f"wiki/сервисы/Сервис {i}.md", f"# Сервис {i}\n")
    text = build_index(vault, big=30, today=TODAY)
    assert "- `wiki/сервисы/` — заметок: 31" in text
    assert "[[Сервис 1]]" not in text


def test_small_folder_listed(vault):
    for i in range(3):
        write(vault, f"wiki/сервисы/Сервис {i}.md", f"# Сервис {i}\n")
    text = build_index(vault, big=30, today=TODAY)
    assert "- **сервисы/**" in text and "[[Сервис 1]]" in text


def test_cards_dir_one_line(vault):
    for i in range(3):
        write(vault, f"content/Разведка/автор/cards/{i}.md", "ролик\n")
    write(vault, "content/Разведка/автор/Разбор.md", "---\ndescription: что залетает\n---\n")
    text = build_index(vault, today=TODAY)
    assert "- `content/Разведка/` — заметок: 4" in text


def test_same_name_with_path(vault):
    write(vault, "projects/Бот/План.md", "# План бота\n")
    text = build_index(vault, today=TODAY)
    assert "[[projects/Бот/План|План (Бот)]]" in text
    assert "[[projects/Сайт студии/План|План (Сайт студии)]]" in text


def test_journal_no_content(vault):
    write(vault, "journal/Секрет.md", "# Секрет\nличное\n")
    text = build_index(vault, today=TODAY)
    assert "Секрет" not in text
    assert "- `journal/` — заметок: 1. Читать только по прямой просьбе человека." in text


def test_describe_order(tmp_path):
    a = write(tmp_path, "a.md", "---\ndescription: из описания\nтема: из темы\n---\n## For future agent\nиз абзаца\n")
    b = write(tmp_path, "b.md", "---\nтема: из темы заметки\n---\nтекст\n")
    c = write(tmp_path, "c.md", "# Заголовок\n\n## For future agent\nиз абзаца для агента\n")
    d = write(tmp_path, "d.md", "# Заголовок\n\n| таблица |\n\nПервая содержательная строка заметки.\n")
    e = write(tmp_path, "e.md", "---\ndescription: <одна строка: заглушка>\n---\n<заглушка>\n")
    assert describe(a) == "из описания"
    assert describe(b) == "из темы заметки"
    assert describe(c) == "из абзаца для агента"
    assert describe(d) == "Первая содержательная строка заметки."
    assert describe(e) == ""
    long = write(tmp_path, "f.md", "---\ndescription: " + "я" * 200 + "\n---\n")
    assert len(describe(long)) == 140


def test_missing_sections(vault):
    for d in ("content", "archive", "raw"):
        shutil.rmtree(vault / d)
    text = build_index(vault, today=TODAY)
    assert "## Контент" not in text and "## Архив" not in text and "## Сырьё" not in text
    assert "## Проекты" in text


def test_cyrillic_space_path(tmp_path, vault):
    target = tmp_path / "Второй мозг"
    shutil.copytree(vault, target)
    assert "### Сайт студии" in build_index(target, today=TODAY)


def test_idempotent(vault):
    assert build_index(vault, today=TODAY) == build_index(vault, today=TODAY)


def test_cli_writes_index(vault):
    import subprocess, sys
    from conftest import SCRIPTS
    out = subprocess.run([sys.executable, "-I", str(SCRIPTS / "index.py"), str(vault)],
                         capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0, out.stderr
    assert "### Сайт студии" in (vault / "index.md").read_text(encoding="utf-8")
    assert "index.md:" in out.stdout
