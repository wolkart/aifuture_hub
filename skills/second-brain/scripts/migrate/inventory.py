"""Опись переезда старого волта: что куда.
  python3 -I inventory.py tree <волт> [--depth 3]          — дерево папок с числом заметок
  python3 -I inventory.py build <волт> <rules.json> [--out <папка>]
      → <папка>/plan.json + <папка>/Опись.md (по умолчанию <волт>/_переезд/)
Правила (rules.json): {"rules": [{"from": "папка/" или "путь/начало имени", "to": "новая/папка/" или
"точный/путь.md" или null (не берём), "why": "…", "ask": "" или "вопрос человеку"}]}.
Первое совпадение решает: исключения пишутся раньше общего правила."""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import iter_files, nfc, utf8_stdio, vault_arg, write_text  # noqa: E402

SKIP = {".git", ".obsidian", ".trash", "_переезд"}
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}
NOT_TAKEN = "не берём"


def _files(root: Path) -> list:
    return [p for p in iter_files(root, skip=SKIP) if Path(p).name not in JUNK]


def tree(root: Path, depth: int = 3) -> str:
    root = Path(root)
    md, other = Counter(), Counter()
    for p in _files(root):
        parts = p.split("/")[:-1]
        for i in range(1, min(len(parts), depth) + 1):
            key = "/".join(parts[:i])
            (md if p.endswith(".md") else other)[key] += 1
        if not parts:
            (md if p.endswith(".md") else other)["."] += 1
    lines = []
    for key in sorted(set(md) | set(other), key=lambda k: (k != ".", k)):
        indent = "  " * (0 if key == "." else key.count("/"))
        name = "(корень)" if key == "." else key.split("/")[-1] + "/"
        tail = f", других файлов: {other[key]}" if other[key] else ""
        lines.append(f"{indent}{name} — заметок: {md[key]}{tail}")
    return "\n".join(lines)


def _target(rel: str, rule: dict):
    src, dst = nfc(rule["from"]), rule["to"]
    if dst is None:
        return None
    dst = nfc(dst)
    if src.endswith("/"):
        return dst.rstrip("/") + "/" + rel[len(src):]
    return dst + Path(rel).name if dst.endswith("/") else dst


def build(root: Path, rules: list) -> dict:
    root = Path(root)
    dest, hit, unmatched = {}, defaultdict(list), []
    for rel in _files(root):
        for i, rule in enumerate(rules):
            if rel.startswith(nfc(rule["from"])):
                dest[rel] = _target(rel, rule)
                hit[i].append(rel)
                break
        else:
            unmatched.append(rel)
    taken = Counter(v for v in dest.values() if v)
    names = defaultdict(set)
    for v in dest.values():
        if v and v.endswith(".md"):
            names[Path(v).name].add(v)
    return {
        "rules": rules,
        "dest": dest,
        "hit": {str(i): v for i, v in hit.items()},
        "unmatched": unmatched,
        "collisions": sorted(k for k, n in taken.items() if n > 1),
        "same_name": {k: sorted(v) for k, v in sorted(names.items()) if len(v) > 1},
    }


def _count(paths: list) -> str:
    md = sum(p.endswith(".md") for p in paths)
    other = len(paths) - md
    return f"{md}" + (f" + {other} др." if other else "")


def render(plan: dict, today: str) -> str:
    rules, hit = plan["rules"], plan["hit"]
    summ, summ_md = Counter(), Counter()
    for src, dst in plan["dest"].items():
        key = NOT_TAKEN if dst is None else dst.split("/")[0] + ("/" if "/" in dst else "")
        summ[key] += 1
        summ_md[key] += src.endswith(".md")
    L = ["---", "тип: переезд", "статус: на проверке", f"создано: {today}", "---", "",
         "# Опись — что куда переезжает", "",
         "Как править: скажи агенту «строка 14 — в архив» или поправь `rules.json` рядом. "
         f"`{NOT_TAKEN}` — в новую структуру не переносим, но файл не пропадает: он остаётся в "
         "архиве-снимке Git. Строки с **?** ждут твоего ответа — они собраны в разделе ниже.", "",
         "## Итог", "", "| куда | заметок | всего файлов |", "|---|---:|---:|"]
    for k in sorted(summ, key=lambda k: (k == NOT_TAKEN, k)):
        L.append(f"| `{k}` | {summ_md[k]} | {summ[k]} |")
    L.append(f"| **всего** | **{sum(summ_md.values())}** | **{sum(summ.values())}** |")

    L += ["", "## Вопросы к тебе", ""]
    asks = [(i, r) for i, r in enumerate(rules) if r.get("ask") and hit.get(str(i))]
    for i, r in asks:
        L.append(f"- **Строка {i + 1}.** `{r['from']}` → `{r['to'] or NOT_TAKEN}` — {r['ask']}")
    if not asks:
        L.append("Нет.")

    for title, items in (("Без правила", plan["unmatched"]), ("Коллизии — два файла в одно место", plan["collisions"])):
        if items:
            L += ["", f"## {title}", ""] + [f"- `{p}`" for p in items]
    if plan["same_name"]:
        L += ["", "## Одноимённые заметки — ссылки [[имя]] будут вести только к одной", ""]
        L += [f"- `{k}`: " + ", ".join(f"`{p}`" for p in v) for k, v in plan["same_name"].items()]

    L += ["", "## Таблица", "", "| № | откуда | файлов | куда | почему |", "|---:|---|---:|---|---|"]
    for i, r in enumerate(rules):
        paths = hit.get(str(i))
        if not paths:
            continue
        q = " **?**" if r.get("ask") else ""
        L.append(f"| {i + 1} | `{r['from']}` | {_count(paths)} | `{r['to'] or NOT_TAKEN}`{q} | {r.get('why', '')} |")
    return "\n".join(L) + "\n"


def main(argv=None):
    from datetime import date
    ap = argparse.ArgumentParser(description="Опись переезда старого волта")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tree"); t.add_argument("vault"); t.add_argument("--depth", type=int, default=3)
    b = sub.add_parser("build"); b.add_argument("vault"); b.add_argument("rules"); b.add_argument("--out")
    utf8_stdio()
    a = ap.parse_args(argv)
    if a.cmd == "tree":
        print(tree(vault_arg(a.vault), a.depth))
        return 0
    rules = json.loads(vault_arg(a.rules).read_text(encoding="utf-8"))["rules"]
    plan = build(vault_arg(a.vault), rules)
    out = vault_arg(a.out) if a.out else vault_arg(a.vault) / "_переезд"
    out.mkdir(parents=True, exist_ok=True)
    write_text(out / "plan.json", json.dumps(plan, ensure_ascii=False, indent=1))
    write_text(out / "Опись.md", render(plan, date.today().isoformat()))
    asks = sum(1 for i, r in enumerate(rules) if r.get("ask") and plan["hit"].get(str(i)))
    print(f"файлов: {len(plan['dest']) + len(plan['unmatched'])} | без правила: {len(plan['unmatched'])} | "
          f"коллизий: {len(plan['collisions'])} | одноимённых: {len(plan['same_name'])} | вопросов: {asks}")
    print(f"опись: {out / 'Опись.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
