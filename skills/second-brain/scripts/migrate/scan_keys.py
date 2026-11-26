"""Поиск ключей, токенов и паролей в папке — до первого коммита в Git: из истории их не вычистить.
Запуск: python3 -I scan_keys.py <папка>
Печатает «путь:строка:вид:маска» — само значение никогда, только первые 4 знака. Код выхода 1,
если есть совпадения, не похожие на заглушку. Решение по каждому — глазами."""
import re
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import iter_files, read_text, resolve, utf8_stdio  # noqa: E402

Hit = namedtuple("Hit", "path line kind masked placeholder")

PATTERNS = [
    ("anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{3,}")),
    ("openai", re.compile(r"sk-(?!ant-)[A-Za-z0-9_\-]{3,}")),
    ("github", re.compile(r"(?:ghp|gho|ghu|ghs)_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,}")),
    ("telegram-бот", re.compile(r"\b\d{8,10}:[A-Za-z0-9_\-]{30,}")),
    ("slack", re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("aws", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("google", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("закрытый ключ", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("пароль/токен", re.compile(r"(?i)(?:api[_-]?key|token|secret|password|passwd|пароль)[\"']?\s*[:=]\s*[\"']?([^\s\"',}]{6,})")),
]
PLACEHOLDER = re.compile(r"(?i)x{3,}|your|example|here|ваш|<|\.\.\.|…|\*{3,}|changeme|placeholder|dummy|test")
SKIP = {".git", ".trash"}
MAX_BYTES = 5_000_000


def _masked(value: str) -> str:
    return f"{value[:4]}…({len(value)})"


def _is_placeholder(kind: str, value: str) -> bool:
    if PLACEHOLDER.search(value):
        return True
    return kind in ("openai", "anthropic") and len(value) < 20


def scan(root: Path) -> list:
    root = Path(root)
    hits = []
    for rel in iter_files(root, skip=SKIP):
        p = resolve(root, rel)
        if p.stat().st_size > MAX_BYTES or b"\0" in p.read_bytes()[:4096]:
            continue
        for n, line in enumerate(read_text(p).splitlines(), 1):
            seen = set()
            for kind, rx in PATTERNS:
                for m in rx.finditer(line):
                    value = m.group(m.lastindex or 0)
                    if any(value in s or s in value for s in seen):
                        continue
                    seen.add(value)
                    hits.append(Hit(rel, n, kind, _masked(value), _is_placeholder(kind, value)))
    return hits


if __name__ == "__main__":
    utf8_stdio()
    found = scan(Path(sys.argv[1]))
    for h in found:
        print(f"{h.path}:{h.line}:{h.kind}:{h.masked}" + (" (похоже на заглушку)" if h.placeholder else ""))
    real = sum(not h.placeholder for h in found)
    print(f"совпадений: {len(found)}, похоже на настоящие: {real}. Каждое — посмотреть глазами.")
    sys.exit(1 if real else 0)
