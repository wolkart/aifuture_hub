"""Раздел «Заметки проекта» в карточках projects/<Проект>/<Проект>.md — ссылки на все заметки
папки проекта, по подпапкам. Пересобирается целиком между метками, остальной текст карточки не
трогается. Запуск: python3 -I cards.py <путь к мозгу>"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import iter_files, name_counts, nfc, read_text, wikilink, write_text

START = "<!-- заметки проекта: начало (пересобирается скриптом второго мозга cards.py) -->"
END = "<!-- заметки проекта: конец -->"
EMPTY = "Пока только карточка: материалы проекта живут в его папке (см. «Где живёт»)."


def _block(groups: dict) -> str:
    lines = [START, "## Заметки проекта", ""]
    if not groups:
        lines += [EMPTY, ""]
    for sub in sorted(groups, key=lambda s: (s != ".", s)):
        title = "В корне проекта" if sub == "." else sub
        lines += [f"**{title}:** " + " · ".join(groups[sub]), ""]
    return "\n".join(lines + [END]) + "\n"


def update_cards(root: Path) -> dict:
    root = Path(root)
    pdir = root / "projects"
    if not pdir.is_dir():
        return {}
    counts = name_counts(root)
    result = {}
    for proj_dir in sorted(p for p in pdir.iterdir() if p.is_dir()):
        proj = nfc(proj_dir.name)
        card = proj_dir / f"{proj_dir.name}.md"
        if not card.is_file():
            continue
        groups = {}
        for rel in iter_files(proj_dir):
            if not rel.endswith(".md") or rel == f"{proj}.md":
                continue
            sub = nfc(str(Path(rel).parent.as_posix()))
            groups.setdefault(sub, []).append(wikilink(f"projects/{proj}/{rel}", counts))
        block = _block(groups)
        text = read_text(card)
        if START in text and END in text:
            new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", lambda _: block, text, flags=re.S)
        else:
            new = text.rstrip() + "\n\n" + block
        if new != text:
            write_text(card, new)
        result[proj] = sum(len(v) for v in groups.values())
    return result


if __name__ == "__main__":
    for proj, n in update_cards(Path(sys.argv[1])).items():
        print(f"{proj}: ссылок {n}")
