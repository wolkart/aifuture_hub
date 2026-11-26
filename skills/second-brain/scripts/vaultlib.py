"""Общее для скриптов второго мозга: имена в NFC, обход папки, чтение, вики-ссылки."""
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterator

SKIP_DIRS = {".git", ".obsidian", ".trash", "_переезд"}
LINK_RE = re.compile(r"!?\[\[([^\]|#^]+)")
_CODE_RE = re.compile(r"```.*?```|`[^`\n]*`", re.S)


def nfc(s: str) -> str:
    """Мак хранит «й/ё» в именах файлов разложенными (NFD) — сравнивать только после приведения."""
    return unicodedata.normalize("NFC", s)


def iter_files(root: Path, skip=SKIP_DIRS) -> Iterator[str]:
    """Относительные пути всех файлов, в NFC, с «/» как разделителем; служебные папки пропускаются."""
    root = Path(root)
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if nfc(x) not in skip)
        for f in sorted(files):
            yield nfc(Path(d, f).relative_to(root).as_posix())


def read_text(path: Path) -> str:
    return nfc(Path(path).read_text(encoding="utf-8", errors="replace"))


def strip_code(text: str) -> str:
    """Убрать блоки и вставки кода: `[[…]]` в них — пример, а не ссылка."""
    return _CODE_RE.sub("", text)


def name_counts(root: Path) -> Counter:
    """Сколько заметок с каждым именем (без папки и .md) — одноимённые надо связывать с путём."""
    return Counter(Path(p).stem for p in iter_files(root) if p.endswith(".md"))


def wikilink(rel: str, counts: Counter) -> str:
    """[[имя]], а для одноимённых — [[путь/имя|имя (папка)]], иначе Obsidian свяжет только одну."""
    p = Path(rel)
    if counts.get(p.stem, 0) > 1:
        return f"[[{p.with_suffix('').as_posix()}|{p.stem} ({p.parent.name})]]"
    return f"[[{p.stem}]]"


def write_text(path: Path, text: str) -> None:
    """UTF-8 и \\n в конце строк на любой ОС (на Windows по умолчанию были бы cp1251 и \\r\\n)."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def resolve(root: Path, rel: str) -> Path:
    """Файл на диске по пути в NFC. Мак находит файл при любой форме «й/ё», а Windows сравнивает
    имена побайтно: файл, пришедший с Мака в NFD, по NFC-пути не откроется — ищем имя в папке."""
    p = Path(root) / rel
    if os.path.lexists(p):
        return p
    cur = Path(root)
    for part in Path(rel).parts:
        nxt = cur / part
        if not os.path.lexists(nxt) and cur.is_dir():
            match = next((c for c in os.listdir(cur) if nfc(c) == nfc(part)), None)
            if match is not None:
                nxt = cur / match
        cur = nxt
    return cur


def utf8_stdio() -> None:
    """Вывод скриптов — UTF-8 на любой ОС: на Windows кириллица и «→» в cp1252 роняют print."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
