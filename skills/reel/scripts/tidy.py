#!/usr/bin/env python3
"""Порядок в export/: готовые ролики и, пока идёт работа, _сборка/. Только stdlib.

Два режима:
  в работе (по умолчанию) — автор выбрал вариант: отбракованные варианты (--keep), кадры
      маски, листы проверки и копии медиа в проектах слоёв удаляются, посторонние файлы
      из export/ уезжают в _сборка/.
  --done — автор принял финал, правок больше нет: _сборка/ удаляется целиком, в export/
      остаются только ролики (и их .txt с текстами для публикации). Исходники (запись и звук из cut-list) печатаются списком и
      удаляются только с --sources — то есть после «да» автора на прямой вопрос.

Почему сборка не хранится: к законченному ролику автор не возвращается, а оставленная
возможность вернуться висит незаконченным делом; переделка, если случится, идёт с нуля из
исходников. В прототипе сборка одного ролика доходила до 3,7 ГБ.

По умолчанию — только показать, что будет сделано и сколько места освободится.
Удаляет — с флагом --apply (и только то, что показал).

usage: tidy.py <папка export> [--keep v2 [--keep v4]] [--apply]
       tidy.py <папка export> --done [--sources] [--apply]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

MEDIA = {".mp4", ".mov", ".webm", ".m4a", ".wav"}
SCRATCH_DIRS = {"matte", "check", "frames", "renders"}
BUILD = "_сборка"


def size(p):
    p = Path(p)
    if p.is_symlink() or p.is_file():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())


def is_variant(d):
    return d.is_dir() and (d / "plan.json").exists()


def is_reel(p):
    return p.is_file() and p.suffix.lower() == ".mp4"


def is_reel_text(p):
    """Тексты для публикации рядом с роликом (<имя ролика>.txt) — часть ролика, не мусор
    (урок автора 2026-10-17: копирует тайтл и описание оттуда, YouTube выкладывает позже)."""
    return p.is_file() and p.suffix.lower() == ".txt" and p.with_suffix(".mp4").is_file()


def strays(export):
    """Всё в export/, кроме роликов и _сборка/; старая папка final/ раскрывается по файлам."""
    out = []
    for p in sorted(export.iterdir()) if export.exists() else []:
        if p.name == BUILD or p.name.startswith(".") or is_reel(p) or is_reel_text(p):
            continue
        if p.name == "final" and p.is_dir():
            out += [f for f in sorted(p.iterdir()) if not f.name.startswith(".")]
            continue
        out.append(p)
    return out


def lift_reels(export, items):
    """Ролики из старой final/ — прямо в export/; → (действия, остальное)."""
    acts, rest = [], []
    for p in items:
        if is_reel(p) and p.parent != export:
            acts.append(("move", p, export / p.name, "ролик — прямо в export/"))
        else:
            rest.append(p)
    return acts, rest


def sources(export):
    """Исходники ролика: запись и звук из cut-list; в режиме subs — файл, на который ссылается черновик."""
    build, found = export / BUILD, []
    for cl in sorted(build.glob("*.cutlist.json")) if build.exists() else []:
        try:
            inputs = json.loads(cl.read_text(encoding="utf-8")).get("inputs", {})
        except (ValueError, OSError):
            continue
        for key in ("video", "audio"):
            if inputs.get(key):
                p = Path(inputs[key])
                found.append(p if p.is_absolute() else export.parent / p)
    link = build / "roughcut.mp4"
    if link.is_symlink():
        found.append(link.resolve())
    uniq = []
    for p in found:
        p = p.resolve()
        if p.is_file() and export.resolve() not in p.parents and p not in uniq:
            uniq.append(p)
    return uniq


def plan_tidy(export, keep=()):
    """В работе. → [(действие, путь, куда|None, причина)]; действие: delete | move."""
    export = Path(export)
    build = export / BUILD
    acts, rest = lift_reels(export, strays(export))
    for p in rest:
        acts.append(("move", p, build / p.name, "в export/ только ролики и _сборка/"))
    if build.exists():
        for d in sorted(build.iterdir()):
            if not is_variant(d):
                continue
            if keep and d.name not in keep:
                acts.append(("delete", d, None, "отбракованный вариант"))
                continue
            for sub in sorted(d.iterdir()):
                if sub.is_dir() and sub.name in SCRATCH_DIRS:
                    acts.append(("delete", sub, None, "кадры/листы — результат уже вшит"))
                elif sub.is_dir() and (sub / "index.html").exists():
                    for f in sorted(sub.iterdir()):
                        if f.is_file() and f.suffix.lower() in MEDIA:
                            acts.append(("delete", f, None, "копия медиа в проекте слоя (пересобирается)"))
                    if (sub / "renders").exists():
                        acts.append(("delete", sub / "renders", None, "черновые рендеры HyperFrames"))
    return acts


def plan_done(export, with_sources=False):
    """Работа закончена: в export/ остаются только ролики; исходники — только с with_sources."""
    export = Path(export)
    acts, rest = lift_reels(export, strays(export))
    for p in rest:
        acts.append(("delete", p, None, "работа закончена — в export/ только ролики"))
    if (export / BUILD).exists():
        acts.append(("delete", export / BUILD, None, "работа закончена — сборка не хранится"))
    if with_sources:
        for p in sources(export):
            acts.append(("delete", p, None, "исходник — автор сказал «да»"))
    return acts


def show(path, export):
    try:
        return path.relative_to(export)
    except ValueError:
        return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--keep", action="append", default=[], help="вариант, который остаётся (можно несколько)")
    ap.add_argument("--done", action="store_true", help="финал принят: удалить _сборка/ целиком")
    ap.add_argument("--sources", action="store_true", help="с --done: удалить и исходники (только после «да» автора)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    export = Path(args.export)
    if export.name != "export":
        sys.exit("tidy: ожидается папка export/ рядом с исходниками")
    if args.sources and not args.done:
        sys.exit("tidy: --sources только вместе с --done")
    src = sources(export) if args.done else []
    acts = plan_done(export, args.sources) if args.done else plan_tidy(export, args.keep)
    total = 0
    for act, p, dst, why in acts:
        sz = size(p)
        total += sz if act == "delete" else 0
        arrow = f" → {show(dst, export)}" if dst else ""
        print(f"{'удалить' if act == 'delete' else 'перенести':9s} {show(p, export)}{arrow}  "
              f"({sz / 1e6:.1f} МБ) — {why}")
    if args.done and src and not args.sources:
        print("исходники (останутся; удалить — спроси автора, при «да» — с --sources):")
        for p in src:
            print(f"  {p}  ({size(p) / 1e6:.0f} МБ)")
    if not acts:
        print("порядок: export/ уже чистая")
        return
    print(f"освободится {total / 1e6:.1f} МБ")
    if not args.apply:
        print("это план; выполнить — с --apply")
        return
    for act, p, dst, _ in acts:
        if act == "move":
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dst))
        elif p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        elif p.exists() or p.is_symlink():
            p.unlink()
    final = export / "final"
    if final.is_dir() and not any(f for f in final.iterdir() if not f.name.startswith(".")):
        shutil.rmtree(final)
    reels = len([p for p in export.glob("*.mp4") if p.is_file()])
    build = export / BUILD
    print(f"готово: роликов в export/ — {reels}" + (f", _сборка/ — {size(build) / 1e6:.0f} МБ" if build.exists() else ""))


if __name__ == "__main__":
    main()
