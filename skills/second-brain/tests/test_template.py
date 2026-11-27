"""Шаблон волта: все файлы на месте, правила и настройки такие, как в спеке."""
import json
import re
from pathlib import Path

VAULT = Path(__file__).resolve().parent.parent / "templates" / "vault"
BLOCK = Path(__file__).resolve().parent.parent / "templates" / "agents-block.md"

FILES = ["_CLAUDE.md", "README.md", "About Me.md", "index.md", ".gitignore", ".gitattributes",
         ".claude/CLAUDE.md", ".obsidian/app.json", ".obsidian/templates.json",
         "templates/Карточка проекта.md"]
DIRS = ["projects", "content", "wiki", "raw/входящее", "journal", "archive", "files"]
START = "<!-- заметки проекта: начало (пересобирается скриптом второго мозга cards.py) -->"
END = "<!-- заметки проекта: конец -->"


def read(rel):
    return (VAULT / rel).read_text(encoding="utf-8")


def test_required_files():
    missing = [f for f in FILES if not (VAULT / f).is_file()]
    missing += [d for d in DIRS if not (VAULT / d / ".gitkeep").is_file()]
    assert not missing, missing


def test_six_questions():
    text = read("_CLAUDE.md")
    start = text.index("Куда класть")
    section = text[start:text.index("\n## ", start)]
    order = [section.index(f"`{d}/") for d in ("journal", "projects", "content", "raw", "wiki", "archive")]
    assert order == sorted(order)


def test_gitignore():
    text = read(".gitignore")
    for line in (".obsidian/workspace*.json", ".obsidian/plugins/*/data.json", ".trash/", ".DS_Store", "*.sync-conflict-*"):
        assert line in text.splitlines(), line


def test_gitattributes():
    assert "* text=auto eol=lf" in read(".gitattributes").splitlines()


def test_claude_import():
    assert read(".claude/CLAUDE.md") == "@../_CLAUDE.md\n"


def test_obsidian_settings():
    app = json.loads(read(".obsidian/app.json"))
    assert app["attachmentFolderPath"] == "files"
    assert app["newFileLocation"] == "folder"
    assert app["newFileFolderPath"] == "raw/входящее"
    assert json.loads(read(".obsidian/templates.json"))["folder"] == "templates"


def test_card_markers():
    text = read("templates/Карточка проекта.md")
    assert START in text and END in text and text.index(START) < text.index(END)


def test_agents_block():
    text = BLOCK.read_text(encoding="utf-8")
    assert text.startswith("## Второй мозг")
    assert "<путь к мозгу>/index.md" in text
    assert "<путь к мозгу>/_CLAUDE.md" in text
    assert "Git в этой папке не трогай" in text
    assert "## Память" not in text
    assert not re.search(r"\bвыше\b", text), "ссылка на соседний раздел — блок должен работать один"
