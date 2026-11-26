"""Пути к старому волту в файлах вне волта: настройки скиллов (.env), инструкции агентов, скрипты.
Запуск: python3 -I switch.py --old <старый путь> --new <новый путь> [--plan plan.json] [--dry] <файл>…
Меняет только полные пути (старый корень и всё, что под ним; с планом — и переехавшие внутри волта
пути). Голые имена папок вроде «files/» не трогает: в чужом файле они могут значить что угодно.
Содержимое файлов не печатает (в .env лежат ключи) — только «N замен, осталось старых: M  файл»."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import PathRewriter, nfc, read_text, utf8_stdio, write_text  # noqa: E402


def _roots(old: str, new: str) -> dict:
    old, new = nfc(old.rstrip("/")), nfc(new.rstrip("/"))
    roots = {old: new}
    home = nfc(os.path.expanduser("~"))
    if old.startswith(home + "/"):
        roots["~" + old[len(home):]] = ("~" + new[len(home):]) if new.startswith(home + "/") else new
    return roots


def _pairs(roots: dict, plan) -> dict:
    pairs = dict(roots)
    if plan:
        for o_root, n_root in roots.items():
            for r in plan["rules"]:
                if r["from"].endswith("/") and r["to"]:
                    pairs[f"{o_root}/{nfc(r['from']).rstrip('/')}"] = f"{n_root}/{nfc(r['to']).rstrip('/')}"
            for src, dst in plan["dest"].items():
                if dst and src != dst:
                    pairs[f"{o_root}/{nfc(src)}"] = f"{n_root}/{nfc(dst)}"
    return pairs


def run(files: list, old: str, new: str, plan, dry: bool) -> list:
    roots = _roots(old, new)
    rewriter = PathRewriter(_pairs(roots, plan), anchors=set(roots))
    leftover = PathRewriter({r: r for r in roots}, anchors=set(roots))
    out = []
    for f in files:
        p = Path(os.path.expanduser(str(f)))
        t = read_text(p)
        changed, n = rewriter.sub(t)
        if n and not dry:
            write_text(p, changed)
        out.append((str(f), n, leftover.sub(changed)[1]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Пути к старому волту → новый мозг в файлах вне волта")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("files", nargs="+")
    utf8_stdio()
    a = ap.parse_args(argv)
    plan = json.loads(Path(os.path.expanduser(a.plan)).read_text(encoding="utf-8")) if a.plan else None
    old, new = os.path.expanduser(a.old), os.path.expanduser(a.new)
    for f, n, left in run(a.files, old, new, plan, a.dry):
        print(f"{n:3} замен, осталось старых: {left}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
