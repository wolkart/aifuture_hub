"""Перенос старого волта по плану описи (inventory.py build → plan.json).
Запуск: python3 -I move.py <волт> <plan.json> [--dry]
1) битые [[ссылки]] до; 2) папки, отличающиеся только регистром, — в два шага; 3) перенос файлов
(занятое место — остановка до первого переноса); 4) пути в тексте заметок, баз и холстов;
5) [[ссылки]] на переименованные заметки; 6) папки в настройках Obsidian; 7) битые ссылки после.
Проба (--dry) ничего не меняет, но считает, сколько файлов перенесётся и сколько заметок поправится."""
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # python3 -I не добавляет папку скрипта сам

from links import broken_links  # noqa: E402
from vaultlib import (SKIP_DIRS, PathRewriter, iter_files, nfc, read_text, resolve,  # noqa: E402
                      utf8_stdio, vault_arg, write_text)

TEXT_EXT = (".md", ".base", ".canvas")
FOLDERISH = re.compile(r"(?i)folder|path|dir|location|template")
JSON_STR = re.compile(r'"((?:[^"\\]|\\.)*)"(\s*:)?')


def folder_pairs(plan: dict) -> dict:
    """«старая папка» → «новая папка» (без «/» на конце) для правил на папку, которые переносят."""
    return {nfc(r["from"]).rstrip("/"): nfc(r["to"]).rstrip("/") for r in plan["rules"]
            if r["from"].endswith("/") and r["to"]}


def text_pairs(plan: dict) -> dict:
    pairs = dict(folder_pairs(plan))
    for src, dst in plan["dest"].items():
        if dst and src != dst:
            pairs[src] = dst
            if src.endswith(".md") and "/" in src:   # у заметки из корня путь без .md — просто слово
                pairs[src[:-3]] = dst[:-3]
    return pairs


def renamed_stems(plan: dict) -> dict:
    return {Path(s).stem: Path(d).stem for s, d in plan["dest"].items()
            if d and s.endswith(".md") and Path(s).stem != Path(d).stem}


def _map_value(value: str, pairs: dict, folders: dict, folderish: bool):
    """Строка-значение из настроек Obsidian: путь — переписать; голое имя папки — только у ключа-папки."""
    parts = nfc(value).split("/")
    for i in range(len(parts), 0, -1):
        head = "/".join(parts[:i])
        if head in pairs:
            if i == len(parts) and head in folders and not folderish:
                return None   # «name": "Habits" в манифесте плагина — не путь
            return "/".join([pairs[head]] + parts[i:])
    return None


def _rewrite_obsidian(root: Path, plan: dict, dry: bool) -> list:
    pairs, folders = text_pairs(plan), folder_pairs(plan)
    obs = root / ".obsidian"
    if not obs.is_dir() or not pairs:
        return []
    files = [p for p in obs.glob("*.json") if not p.name.startswith("workspace")]
    files += sorted(obs.glob("plugins/*/data.json"))
    fixed = []
    for p in sorted(files):
        t = read_text(p)

        def repl(m):
            if m.group(2):
                return m.group(0)   # ключ, не значение
            try:
                value = json.loads('"' + m.group(1) + '"')
            except ValueError:
                return m.group(0)
            key = re.search(r'"([^"]*)"\s*:\s*$', t[max(0, m.start() - 200):m.start()])
            new = _map_value(value, pairs, folders, bool(key and FOLDERISH.search(key.group(1))))
            return m.group(0) if new is None else json.dumps(new, ensure_ascii=False)

        new = JSON_STR.sub(repl, t)
        if new != t:
            fixed.append(p.relative_to(root).as_posix())
            if not dry:
                write_text(p, new)
    return fixed


def _case_renames(root: Path, plan: dict, dry: bool) -> None:
    """Мак не различает регистр: bases → Bases через временное имя, иначе папка останется bases."""
    for o, n in folder_pairs(plan).items():
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
        d, s = root / dst, resolve(root, src)
        if d.exists() and dst not in dest and not (os.path.exists(s) and os.path.samefile(s, d)):
            busy.append(dst)
    if busy:
        raise SystemExit("занято — переносить некуда, ничего не тронуто:\n  " + "\n  ".join(busy))


def run(root: Path, plan: dict, dry: bool) -> dict:
    root = Path(root)
    dest = {nfc(k): (nfc(v) if v else None) for k, v in plan["dest"].items()}
    stems = renamed_stems(plan)
    before = broken_links(root)
    _check_targets(root, dest)
    _case_renames(root, plan, dry)

    moved = skipped = 0
    for src, dst in dest.items():
        s = resolve(root, src)
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

    paths = PathRewriter(text_pairs(plan))
    links = PathRewriter({"[[" + o: "[[" + n for o, n in stems.items()}, anchors={"[["}) if stems else None
    rewritten = 0
    for rel in iter_files(root):
        if not rel.endswith(TEXT_EXT):
            continue
        f = resolve(root, rel)
        t = read_text(f)
        new, _ = paths.sub(t)
        if links:
            new, _ = links.sub(new)
        if new != t:
            rewritten += 1
            if not dry:
                write_text(f, new)

    obsidian = _rewrite_obsidian(root, plan, dry)
    moved_note = {s: d for s, d in dest.items() if d}
    key = lambda note, target: (note, stems.get(target.split("/")[-1], target.split("/")[-1]))  # noqa: E731
    was = {key(moved_note.get(n, n), t) for n, t in before}
    if dry:
        after, new_broken = before, []
    else:
        after = broken_links(root)
        new_broken = sorted(b for b in after if key(*b) not in was)
    return {"moved": moved, "skipped": skipped, "rewritten": rewritten, "obsidian": obsidian,
            "broken_before": len(before), "broken_after": len(after), "new_broken": new_broken}


if __name__ == "__main__":
    utf8_stdio()
    args = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv
    r = run(vault_arg(args[0]), json.loads(vault_arg(args[1]).read_text(encoding="utf-8")), dry=dry)
    print(("ПРОБА, ничего не изменено. " if dry else "") +
          f"перенесено: {r['moved']} | не взято: {r['skipped']} | заметок с поправленными путями: {r['rewritten']}")
    print(f"настройки Obsidian: {', '.join(r['obsidian']) or 'без изменений'}")
    if dry:
        print(f"битых ссылок сейчас: {r['broken_before']} (новые битые проба не считает — их покажет перенос)")
    else:
        print(f"битых ссылок до: {r['broken_before']} | после: {r['broken_after']} | новых: {len(r['new_broken'])}")
    for note, target in r["new_broken"][:40]:
        print(f"   {note} → {target}")
    sys.exit(1 if r["new_broken"] else 0)
