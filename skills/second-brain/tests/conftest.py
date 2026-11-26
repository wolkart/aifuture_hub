import shutil
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
TEMPLATE = SKILL / "templates" / "vault"
sys.path.insert(0, str(SCRIPTS))


def write(root: Path, rel: str, text: str = "") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def vault(tmp_path):
    """Свежий мозг из шаблона + два проекта: в одном заметки (в корне и в подпапке), другой пустой."""
    root = tmp_path / "brain"
    shutil.copytree(TEMPLATE, root)
    card = (TEMPLATE / "templates" / "Карточка проекта.md").read_text(encoding="utf-8")
    for proj in ("Сайт студии", "Бот"):
        write(root, f"projects/{proj}/{proj}.md", card.replace("{{title}}", proj))
    write(root, "projects/Сайт студии/План.md", "---\ndescription: план сайта\n---\n# План\n")
    write(root, "projects/Сайт студии/Дизайн/Макет.md", "# Макет\n\n[[План]]\n")
    return root
