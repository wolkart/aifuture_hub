"""Пути к старому волту в файлах вне волта: настройки скиллов (.env), инструкции агентов, скрипты.
Запуск: python3 -I switch.py --old <старый путь> --new <новый путь> [--plan plan.json] [--dry] <файл>…
С планом заменяет и пути внутри волта, которые переехали. Содержимое файлов не печатает (в .env
лежат ключи) — только «N замен, осталось старых: M  файл»."""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from vaultlib import nfc, read_text, write_text  # noqa: E402


def _pairs(old: str, new: str, plan) -> dict:
    old, new = nfc(old.rstrip("/")), nfc(new.rstrip("/"))
    roots = {old: new}
    home = nfc(os.path.expanduser("~"))
    for o, n in list(roots.items()):
        if o.startswith(home + "/"):
            roots["~" + o[len(home):]] = ("~" + n[len(home):]) if n.startswith(home + "/") else n
    pairs = dict(roots)
    if plan:
        for o_root, n_root in roots.items():
            for src, dst in plan["dest"].items():
                if dst and src != dst:
                    pairs[f"{o_root}/{nfc(src)}"] = f"{n_root}/{nfc(dst)}"
            for r in plan["rules"]:
                if r["from"].endswith("/") and r["to"]:
                    pairs[f"{o_root}/{nfc(r['from'])}"] = f"{n_root}/{nfc(r['to']).rstrip('/')}/"
                    pairs.setdefault(nfc(r["from"]), nfc(r["to"]).rstrip("/") + "/")
    return pairs


def run(files: list, old: str, new: str, plan, dry: bool) -> list:
    pairs = _pairs(old, new, plan)
    rx = re.compile("|".join(re.escape(k) for k in sorted(pairs, key=len, reverse=True)))
    old_rx = re.compile("|".join(re.escape(k) for k in sorted(
        [k for k in pairs if not k.startswith((nfc(new.rstrip("/")),))], key=len, reverse=True)))
    out = []
    for f in files:
        p = Path(os.path.expanduser(str(f)))
        t = read_text(p)
        changed, n = rx.subn(lambda m: pairs[m.group(0)], t)
        result = t if dry else changed
        if n and not dry:
            write_text(p, changed)
        left = len(old_rx.findall(result)) if dry else len(re.findall(re.escape(nfc(old.rstrip("/"))), result))
        out.append((str(f), n, left))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Пути к старому волту → новый мозг в файлах вне волта")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else None
    for f, n, left in run(a.files, a.old, a.new, plan, a.dry):
        print(f"{n:3} замен, осталось старых: {left}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
