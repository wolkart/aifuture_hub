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


KEY = "sk-proj-" + "a1B2c3D4e5" * 4
TG_TOKEN = "1234567890:" + "AAH" + "x9Yz" * 8


@pytest.fixture
def messy_vault(tmp_path):
    """Старый волт «как бывает»: PARA-папки, bases строчными, дубль облака «(2)», одноимённые
    заметки, имя в NFD, база с фильтром по папке, папка вложений в настройках, ключи и заглушка."""
    import unicodedata
    root = tmp_path / "old vault"
    w = lambda rel, text="": write(root, rel, text)
    w("0-Входящие/Идея.md", "# Идея\n\nсм. [[Рилс про ботов]]\n")
    w("2-Контент/Рилсы/Рилс про ботов.md", "# Рилс\n\n[[Идея]]\nфайл: 2-Контент/Рилсы/Рилс про ботов.md\n")
    w("bases/Контент.base", 'filters:\n  and:\n    - file.inFolder("2-Контент")\n')
    w("Заметка.md", "# Заметка\n")
    w("Заметка (2).md", "# Заметка\n")
    w("Проекты/Сайт/План.md", "# План сайта\n")
    w("Проекты/Бот/План.md", "# План бота\n")
    w("Ресурсы/" + unicodedata.normalize("NFD", "Йога") + ".md", "# Йога\n\n[[Заметка]]\n")
    w(".obsidian/app.json", '{\n  "attachmentFolderPath": "Вложения"\n}\n')
    w(".obsidian/plugins/copilot/data.json", '{"openAIApiKey": "%s"}\n' % KEY)
    w("Вложения/картинка.png", "")
    w(".env", f"OPENAI_API_KEY={KEY}\nTELEGRAM_TOKEN={TG_TOKEN}\n")
    w("README.md", "Пример ключа: sk-xxx, токен: your_token_here\n")
    return root


@pytest.fixture
def rules():
    return [
        {"from": "0-Входящие/", "to": "archive/Входящие/", "why": "старые входящие", "ask": ""},
        {"from": "2-Контент/", "to": "content/", "why": "контент", "ask": ""},
        {"from": "bases/", "to": "Bases/", "why": "базы Obsidian", "ask": ""},
        {"from": "Заметка (2).md", "to": None, "why": "дубль облака", "ask": ""},
        {"from": "Заметка.md", "to": "wiki/", "why": "знание", "ask": "это знание или дневник?"},
        {"from": "Проекты/", "to": "projects/", "why": "проекты", "ask": ""},
        {"from": "Ресурсы/", "to": "wiki/", "why": "знания", "ask": ""},
        {"from": "Вложения/", "to": "files/", "why": "вложения", "ask": ""},
        {"from": "README.md", "to": "archive/", "why": "старое описание", "ask": ""},
    ]
