#!/usr/bin/env python3
"""Порядок в export/: ровно final/ и _сборка/, без мусора. Только stdlib.

В прототипе демо-варианты, кадры и маски копились — папка разрослась до тысяч файлов и
3,7 ГБ, автор отметил это как проблему. Правило: отбракованный вариант удаляется сразу,
как автор выбрал; кадры маски, листы проверки и копии медиа внутри проектов —
после того, как результат вшит. Проекты, план, cut-list, черновик, звук и слои
выбранного варианта остаются: это снимок сборки, по нему ролик пересобирается.

По умолчанию — только показать, что будет сделано и сколько места освободится.
Удаляет — с флагом --apply (и только то, что показал).

usage: tidy.py <папка export> [--keep v2 [--keep v4]] [--apply]
"""
import argparse
import shutil
import sys
from pathlib import Path

MEDIA = {".mp4", ".mov", ".webm", ".m4a", ".wav"}
SCRATCH_DIRS = {"matte", "check", "frames", "renders"}


def size(p):
    p = Path(p)
    if p.is_symlink() or p.is_file():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())


def is_variant(d):
    return d.is_dir() and (d / "plan.json").exists()


def plan_tidy(export, keep=()):
    """→ [(действие, путь, куда|None, причина)]; действие: delete | move."""
    export, acts = Path(export), []
    build, final = export / "_сборка", export / "final"
    for p in sorted(export.iterdir()) if export.exists() else []:
        if p.name in ("_сборка", "final") or p.name.startswith("."):
            continue
        acts.append(("move", p, build / p.name, "в export/ только final/ и _сборка/"))
    if final.exists():
        for p in sorted(final.iterdir()):
            if p.name.startswith(".") or p.name == "README.md" or p.suffix.lower() == ".mp4":
                continue
            acts.append(("move", p, build / p.name, "в final/ только готовые ролики и README"))
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--keep", action="append", default=[], help="вариант, который остаётся (можно несколько)")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    export = Path(args.export)
    if export.name != "export":
        sys.exit("tidy: ожидается папка export/ рядом с исходниками")
    acts = plan_tidy(export, args.keep)
    if not acts:
        print("порядок: export/ уже чистая")
        return
    total = 0
    for act, p, dst, why in acts:
        sz = size(p)
        total += sz if act == "delete" else 0
        arrow = f" → {dst.relative_to(export)}" if dst else ""
        print(f"{'удалить' if act == 'delete' else 'перенести':9s} {p.relative_to(export)}{arrow}  "
              f"({sz / 1e6:.1f} МБ) — {why}")
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
        else:
            p.unlink()
    build = export / "_сборка"
    print(f"готово: final/ — {len(list((export / 'final').glob('*.mp4')))} роликов, "
          f"_сборка/ — {size(build) / 1e6:.0f} МБ" if build.exists() else "готово")


if __name__ == "__main__":
    main()
