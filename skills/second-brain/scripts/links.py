"""Битые [[ссылки]] во втором мозге. Запуск: python3 -I links.py <путь к мозгу>
Печатает «заметка → цель» по строке, код выхода 1, если битые есть."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import LINK_RE, iter_files, nfc, read_text, resolve, strip_code, utf8_stdio, vault_arg


def broken_links(root: Path) -> set:
    root = Path(root)
    files = list(iter_files(root))
    names = {Path(p).name for p in files}
    stems = {Path(p).stem.strip() for p in files if p.endswith(".md")}   # «Заметка .md» — ссылка [[Заметка ]]
    bad = set()
    for rel in files:
        if not rel.endswith(".md") or "/cards/" in f"/{rel}":
            continue
        for m in LINK_RE.finditer(strip_code(read_text(resolve(root, rel)))):
            target = nfc(m.group(1).strip().rstrip("\\").strip())
            name = target.split("/")[-1]
            if not name or name in stems or name in names or f"{name}.md" in names:
                continue
            bad.add((rel, target))
    return bad


if __name__ == "__main__":
    utf8_stdio()
    found = sorted(broken_links(vault_arg(sys.argv[1])))
    for note, target in found:
        print(f"{note} → {target}")
    print(f"битых ссылок: {len(found)}")
    sys.exit(1 if found else 0)
