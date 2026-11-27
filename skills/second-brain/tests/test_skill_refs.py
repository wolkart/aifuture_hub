"""Каждая ссылка на файл скилла из SKILL.md, README.md и references/ ведёт на существующий файл."""
import re
from pathlib import Path

from conftest import SKILL

MD_LINK = re.compile(r"\]\(((?!https?:)[^)#\s]+)\)")
SKILL_PATH = re.compile(r"<скилл>[/\\]((?:scripts|templates|references)[^`\"'\n]*)")


def _skill_path_ok(raw: str):
    """Путь после <скилл>/ — до кавычки или конца строки; лишний хвост («<мозг>», «в корень») срезаем по пробелам."""
    rel = raw.replace("\\", "/").strip()
    while True:
        rel = rel.rstrip("*/.) ")
        if (SKILL / rel).exists():
            return None
        if " " not in rel:
            return rel
        rel = rel.rsplit(" ", 1)[0]


def missing_refs(md: Path) -> list:
    text = md.read_text(encoding="utf-8")
    out = [m for m in MD_LINK.findall(text) if not (md.parent / m).exists()]
    out += [bad for bad in map(_skill_path_ok, SKILL_PATH.findall(text)) if bad]
    return out


def test_refs_exist():
    docs = [SKILL / "SKILL.md", SKILL / "README.md", *sorted((SKILL / "references").glob("*.md"))]
    bad = {str(d.relative_to(SKILL)): missing_refs(d) for d in docs}
    assert not {k: v for k, v in bad.items() if v}


def test_missing_ref_is_caught(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("см. [справку](references/нет.md) и `<скилл>/scripts/нет.py`\n", encoding="utf-8")
    assert missing_refs(md) == ["references/нет.md", "scripts/нет.py"]
