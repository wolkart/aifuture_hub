"""Перенос старого волта по плану описи (inventory.py build → plan.json).
Запуск: python3 -I move.py <волт> <plan.json> [--dry]
1) битые [[ссылки]] до; 2) папки, отличающиеся только регистром, — в два шага; 3) перенос файлов
(занятое место — остановка до первого переноса); 4) пути в тексте заметок, баз и холстов;
5) [[ссылки]] на переименованные заметки; 6) папки в настройках Obsidian; 7) битые ссылки после."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from links import broken_links  # noqa: E402
from vaultlib import SKIP_DIRS, iter_files, nfc, read_text, write_text  # noqa: E402

TEXT_EXT = (".md", ".base", ".canvas")


def _folder_rules(plan: dict) -> dict:
    """«старая/» → «новая/» для правил на папку, которые переносят, а не выбрасывают."""
    return {nfc(r["from"]): nfc(r["to"]).rstrip("/") + "/" for r in plan["rules"]
            if r["from"].endswith("/") and r["to"]}


def _text_pairs(plan: dict) -> dict:
    pairs = {}
    for src, dst in plan["dest"].items():
        if dst and src != dst:
            pairs[src] = dst
            if src.endswith(".md") and "/" in src:   # у заметки из корня путь без .md — просто слово
                pairs[src[:-3]] = dst[:-3]
    for old, new in _folder_rules(plan).items():
        pairs.setdefault(old, new)
    return pairs


def _renamed_stems(plan: dict) -> dict:
    out = {}
    for src, dst in plan["dest"].items():
        if dst and src.endswith(".md") and Path(src).stem != Path(dst).stem:
            out[Path(src).stem] = Path(dst).stem
    return out


def _sub_all(text: str, pairs: dict) -> str:
    if not pairs:
        return text
    rx = re.compile("|".join(re.escape(k) for k in sorted(pairs, key=len, reverse=True)))
    return rx.sub(lambda m: pairs[m.group(0)], text)


def _case_renames(root: Path, plan: dict, dry: bool) -> None:
    """Мак не различает регистр: bases → Bases через временное имя, иначе папка останется bases."""
    for old, new in _folder_rules(plan).items():
        o, n = old.rstrip("/"), new.rstrip("/")
        if o != n and o.lower() == n.lower() and "/" not in o and (root / o).is_dir() and not dry:
            names = {nfc(x) for x in os.listdir(root)}
            if o in names and n not in names:
                os.rename(root / o, root / (o + ".tmp-case"))
                os.rename(root / (o + ".tmp-case"), root / n)


def _check_targets(root: Path, dest: dict) -> None:
    busy = []
    for src, dst in dest.items():
        if not dst or src == dst:
            continue
        d = root / dst
        if d.exists() and dst not in dest and not (os.path.exists(root / src) and os.path.samefile(root / src, d)):
            busy.append(dst)
    if busy:
        raise SystemExit("занято — переносить некуда, ничего не тронуто:\n  " + "\n  ".join(busy))


def _rewrite_obsidian(root: Path, plan: dict, dry: bool) -> list:
    folders = {o.rstrip("/"): n.rstrip("/") for o, n in _folder_rules(plan).items()}
    if not folders:
        return []
    rx = re.compile(r'(":\s*")(' + "|".join(re.escape(k) for k in sorted(folders, key=len, reverse=True)) + r')(/|")')
    fixed = []
    obs = root / ".obsidian"
    for p in sorted(obs.rglob("*.json")) if obs.is_dir() else []:
        if p.name.startswith("workspace"):
            continue
        t = read_text(p)
        new = rx.sub(lambda m: m.group(1) + folders[m.group(2)] + m.group(3), t)
        if new != t:
            fixed.append(p.relative_to(root).as_posix())
            if not dry:
                write_text(p, new)
    return fixed


def run(root: Path, plan: dict, dry: bool) -> dict:
    root = Path(root)
    dest = {nfc(k): (nfc(v) if v else None) for k, v in plan["dest"].items()}
    before = broken_links(root)
    _check_targets(root, dest)
    _case_renames(root, plan, dry)

    moved = skipped = 0
    for src, dst in dest.items():
        s = root / src
        if not os.path.lexists(s):
            continue
        if dst is None:
            skipped += 1
            if not dry:
                s.unlink()
            continue
        if src == dst:
            continue
        d = root / dst
        if os.path.exists(d) and os.path.samefile(s, d):
            continue
        moved += 1
        if not dry:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
    if not dry:
        for d, dirs, files in os.walk(root, topdown=False):
            rel = Path(d).relative_to(root).parts
            if d != str(root) and not any(nfc(x) in SKIP_DIRS for x in rel) and not os.listdir(d):
                os.rmdir(d)

    pairs, stems = _text_pairs(plan), _renamed_stems(plan)
    folders = {o.rstrip("/"): n.rstrip("/") for o, n in _folder_rules(plan).items()}
    quoted = {q + o + q: q + n + q for o, n in folders.items() for q in ('"', "'")}
    link_rx = re.compile(r"\[\[(" + "|".join(re.escape(k) for k in sorted(stems, key=len, reverse=True)) + r")(?=[\]|#^])") if stems else None
    rewritten = 0
    for rel in ([] if dry else iter_files(root)):
        if not rel.endswith(TEXT_EXT):
            continue
        t = read_text(root / rel)
        new = _sub_all(t, pairs)
        if rel.endswith((".base", ".canvas")):
            new = _sub_all(new, quoted)
        if link_rx:
            new = link_rx.sub(lambda m: "[[" + stems[m.group(1)], new)
        if new != t:
            write_text(root / rel, new)
            rewritten += 1

    obsidian = _rewrite_obsidian(root, plan, dry)
    after = before if dry else broken_links(root)
    moved_note = {s: d for s, d in dest.items() if d}
    was = {(moved_note.get(n, n), stems.get(t, t)) for n, t in before}
    new_broken = sorted(after - was)
    return {"moved": moved, "skipped": skipped, "rewritten": rewritten, "obsidian": obsidian,
            "broken_before": len(before), "broken_after": len(after), "new_broken": new_broken}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--dry"]
    r = run(Path(args[0]), json.loads(Path(args[1]).read_text(encoding="utf-8")), dry="--dry" in sys.argv)
    print(("ПРОБА, ничего не изменено. " if "--dry" in sys.argv else "") +
          f"перенесено: {r['moved']} | не взято: {r['skipped']} | заметок с поправленными путями: {r['rewritten']}")
    print(f"настройки Obsidian: {', '.join(r['obsidian']) or 'без изменений'}")
    print(f"битых ссылок до: {r['broken_before']} | после: {r['broken_after']} | новых: {len(r['new_broken'])}")
    for note, target in r["new_broken"][:40]:
        print(f"   {note} → {target}")
    sys.exit(1 if r["new_broken"] else 0)
