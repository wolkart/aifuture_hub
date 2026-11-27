"""Собирает каталог index.md второго мозга по правилам _CLAUDE.md.

Проекты и знания — строкой на заметку; большая папка (больше --big заметок) и папка cards/ —
одной строкой; контент, сырьё и архив — строкой на папку; дневник — одной строкой без
содержимого. Запуск: python3 -I index.py <путь к мозгу> [--big 30]"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import iter_files, name_counts, nfc, read_text, resolve, utf8_stdio, vault_arg, wikilink, write_text

SERVICE = {"index.md", "README.md", "_CLAUDE.md", "AGENTS.md", "About Me.md"}
_FM = re.compile(r"^---\n(.*?)\n---\n?", re.S)
_CARD_BLOCK = re.compile(r"<!-- заметки проекта: начало.*?<!-- заметки проекта: конец -->", re.S)


def describe(path: Path) -> str:
    """Одна строка о заметке: description → тема → абзац после «For future agent» → первая строка."""
    text = read_text(path)
    fm = _FM.match(text)
    body = _CARD_BLOCK.sub("", text[fm.end():] if fm else text)
    candidates = []
    if fm:
        for key in ("description", "тема"):
            m = re.search(rf"^{key}:\s*(.+)$", fm.group(1), re.M)
            if m:
                candidates.append(m.group(1))
    m = re.search(r"## For future agent\s*\n+(.+)", body)
    if m:
        candidates.append(m.group(1))
    for line in body.splitlines():
        s = line.strip().lstrip(">").strip().lstrip("-*").strip()
        if s and not s.startswith(("#", "|", "```", "![[", "%%", "---", "<")) and len(s) > 15:
            candidates.append(re.sub(r"\*\*|`|\[\[|\]\]", "", s))
            break
    for c in candidates:
        c = c.strip().strip('"').strip("'").strip()
        if c and not c.startswith("<"):
            return c[:140]
    return ""


class _Catalog:
    def __init__(self, root: Path, big: int):
        self.root, self.big = root, big
        self.counts = name_counts(root)
        self.notes = [p for p in iter_files(root) if p.endswith(".md")]

    def under(self, folder: str) -> list:
        return [p for p in self.notes if p.startswith(folder + "/")]

    def item(self, rel: str, prefix: str = "") -> str:
        desc = describe(resolve(self.root, rel))
        return f"- {prefix}{wikilink(rel, self.counts)}" + (f" — {desc}" if desc else "")

    def count_line(self, folder: str, tail: str = "") -> str:
        return f"- `{folder}/` — заметок: {len(self.under(folder))}{tail}"

    def subdirs(self, folder: str) -> list:
        d = resolve(self.root, folder)
        return sorted(nfc(x.name) for x in d.iterdir() if x.is_dir()) if d.is_dir() else []

    def direct(self, folder: str) -> list:
        return [p for p in self.under(folder) if "/" not in p[len(folder) + 1:]]

    def tree(self, folder: str, indent: str = "", skip=()) -> list:
        """Заметки папки, потом подпапки; большая подпапка или cards/ — одной строкой."""
        out = [indent + self.item(p) for p in self.direct(folder) if p not in skip]
        for sub in self.subdirs(folder):
            path = f"{folder}/{sub}"
            n = len(self.under(path))
            if n == 0:
                continue
            if sub == "cards" or n > self.big:
                out.append(indent + self.count_line(path))
            else:
                out.append(f"{indent}- **{sub}/**")
                out += self.tree(path, indent + "  ")
        return out


def build_index(root: Path, big: int = 30, today: str = None) -> str:
    root = Path(root)
    c = _Catalog(root, big)
    exists = lambda d: (root / d).is_dir()
    L = ["---", f"date: {today or date.today().isoformat()}", "type: index", "tags: [index]",
         "description: Каталог второго мозга — читать первым", "---", "",
         "# Каталог второго мозга", "",
         "Читай первым. Проекты и знания — по строке на заметку, большие папки — строкой на папку.",
         "Правила — `_CLAUDE.md`. Пересобирается скриптом `index.py` скилла second-brain.", ""]

    L += ["## Обо мне", ""]
    if (root / "About Me.md").is_file():
        desc = describe(root / "About Me.md")
        L.append("- [[About Me|Обо мне]]" + (f" — {desc}" if desc else ""))
    L.append("")

    extra = [p for p in c.notes if "/" not in p and p not in SERVICE]
    if extra:
        L += ["## В корне", ""] + [c.item(p) for p in extra] + [""]

    if exists("projects"):
        L += ["## Проекты", ""]
        for proj in c.subdirs("projects"):
            folder = f"projects/{proj}"
            card = f"{folder}/{proj}.md"
            L.append(f"### {proj}")
            if card in c.notes:
                desc = describe(resolve(root, card))
                L.append(f"- {wikilink(card, c.counts)} — карточка проекта" + (f": {desc}" if desc else ""))
            L += c.tree(folder, skip={card})
            L.append("")

    if exists("wiki"):
        L += ["## Знания — wiki/", ""] + c.tree("wiki") + [""]

    if exists("content"):
        L += ["## Контент — content/", ""]
        L += [c.item(p) for p in c.direct("content")]
        L += [c.count_line(f"content/{s}") for s in c.subdirs("content")]
        L.append("")

    if exists("raw"):
        L += ["## Сырьё — raw/ (не править)", ""]
        L += [c.item(p) for p in c.direct("raw")]
        for s in c.subdirs("raw"):
            tail = "; разложить по правилу из `_CLAUDE.md`" if s == "входящее" else ""
            L.append(c.count_line(f"raw/{s}", tail))
        L.append("")

    if exists("journal"):
        L += ["## Дневник — journal/", "",
              c.count_line("journal", ". Читать только по прямой просьбе человека."), ""]

    if exists("archive"):
        L += ["## Архив — archive/ (история, не переписывать)", ""]
        L += [c.item(p) for p in c.direct("archive")]
        L += [c.count_line(f"archive/{s}") for s in c.subdirs("archive")]
        L.append("")

    if exists("templates"):
        L += ["## Шаблоны — templates/", ""] + c.tree("templates") + [""]

    known = {"projects", "wiki", "content", "raw", "journal", "archive", "templates"}
    others = [d for d in c.subdirs(".") if d not in known and not d.startswith(".") and c.under(d)]
    if others:
        L += ["## Другие папки", ""] + [c.count_line(d) for d in others] + [""]

    return re.sub(r"\n{3,}", "\n\n", "\n".join(L)).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Пересобрать index.md второго мозга")
    ap.add_argument("vault")
    ap.add_argument("--big", type=int, default=30, help="больше стольких заметок — папка одной строкой")
    utf8_stdio()
    a = ap.parse_args(argv)
    root = vault_arg(a.vault)
    text = build_index(root, a.big)
    write_text(root / "index.md", text)
    print(f"index.md: {text.count(chr(10))} строк, {len(text)} знаков")


if __name__ == "__main__":
    sys.exit(main())
