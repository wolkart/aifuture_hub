#!/usr/bin/env python3
"""Библиотека моушн-графики: index.json рядом с ассетами. Только stdlib.

Библиотека — папка автора вне репозитория (folders.library в reel.settings.json).
В ней index.json: {"version": 1, "assets": [...]}, запись на ассет:
  id, kind (scene|broll|overlay), layout (full|half|overlay), duration, theme (dark|light),
  tags, describes, events [{t, what}] по возрастанию t, slots, files {mp4, mov_alpha, …};
  у б-ролла ещё transitions [[a, b]] (переходы/наезды) и private [{from, to, what}] —
  запретные окна (IP, ключи, токены, почты).
Пути в files — относительно папки библиотеки. /reel выбирает ассеты отсюда сам:
find() по словам, usable_windows() — куда можно ставить вставку.

CLI:
  library.py list | find <запрос> | show <id> | validate | add <запись.json>
  общие флаги: --library <папка> (иначе folders.library из настроек), --json
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reel" / "scripts"))

INDEX = "index.json"
VERSION = 1
KINDS = ("scene", "broll", "overlay")
LAYOUTS = ("full", "half", "overlay")
THEMES = ("dark", "light")
ID_RE = re.compile(r"[\w][\w.-]*")
EPS = 0.05    # допуск на округление таймкодов относительно длительности


# ── файл ─────────────────────────────────────────────────────────────────────

def index_path(library):
    return Path(library) / INDEX


def empty():
    return {"version": VERSION, "assets": []}


def load(library):
    """index.json библиотеки; нет файла — пустой индекс (файл не создаётся)."""
    p = index_path(library)
    if not p.exists():
        return empty()
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("version", VERSION)
    data.setdefault("assets", [])
    return data


def save(library, index):
    """Записать индекс целиком. Невалидный не пишется: ошибки — ValueError."""
    errors = validate(index)
    if errors:
        raise ValueError("index.json не записан:\n  " + "\n  ".join(errors))
    p = index_path(library)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def put(library, entry):
    """Загрузить → добавить/заменить запись → сохранить. Возвращает путь index.json."""
    index = load(library)
    add_or_replace(index, entry)
    return save(library, index)


# ── валидация ────────────────────────────────────────────────────────────────

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_windows(name, wins, dur, errs):
    if not isinstance(wins, list):
        errs.append(f"{name}: нужен список окон [[a, b], …]")
        return
    for w in wins:
        if not (isinstance(w, (list, tuple)) and len(w) == 2 and all(_num(v) for v in w)):
            errs.append(f"{name}: окно {w!r} — нужно [a, b]")
            continue
        a, b = w
        if a < 0 or b < a or (dur is not None and b > dur + EPS):
            errs.append(f"{name}: окно [{a}, {b}] вне 0…{dur} или a > b")


def validate_entry(entry):
    """Ошибки записи списком строк (пусто — запись годна)."""
    errs = []
    if not isinstance(entry, dict):
        return ["запись должна быть объектом"]
    id_ = entry.get("id")
    if not isinstance(id_, str) or not ID_RE.fullmatch(id_):
        errs.append(f"id {id_!r}: нужна непустая строка из букв, цифр, «-», «_», «.»")
    kind, layout = entry.get("kind"), entry.get("layout")
    if kind not in KINDS:
        errs.append(f"kind {kind!r}: одно из {'|'.join(KINDS)}")
    if layout not in LAYOUTS:
        errs.append(f"layout {layout!r}: одно из {'|'.join(LAYOUTS)}")
    if kind == "overlay" and layout != "overlay":
        errs.append("kind overlay живёт только в layout overlay")
    if entry.get("theme") not in THEMES:
        errs.append(f"theme {entry.get('theme')!r}: одно из {'|'.join(THEMES)}")
    dur = entry.get("duration")
    if not (_num(dur) and dur > 0):
        errs.append(f"duration {dur!r}: положительное число секунд")
        dur = None
    tags = entry.get("tags", [])
    if not (isinstance(tags, list) and all(isinstance(t, str) for t in tags)):
        errs.append("tags: список строк")
    if not isinstance(entry.get("describes", ""), str):
        errs.append("describes: строка")
    prev = None
    for ev in entry.get("events", []) or []:
        if not (isinstance(ev, dict) and _num(ev.get("t")) and isinstance(ev.get("what"), str)
                and ev["what"].strip()):
            errs.append(f"events: {ev!r} — нужно {{t: число, what: текст}}")
            continue
        t = ev["t"]
        if t < 0 or (dur is not None and t > dur + EPS):
            errs.append(f"events: t={t} вне 0…{dur}")
        if prev is not None and t < prev:
            errs.append(f"events: t={t} идёт раньше предыдущего {prev} — нужен порядок по t")
        prev = t
    if "transitions" in entry:
        _check_windows("transitions", entry["transitions"], dur, errs)
    for p in entry.get("private", []) or []:
        if not (isinstance(p, dict) and _num(p.get("from")) and _num(p.get("to"))):
            errs.append(f"private: {p!r} — нужно {{from, to, what}}")
            continue
        if p["from"] < 0 or p["to"] < p["from"] or (dur is not None and p["to"] > dur + EPS):
            errs.append(f"private: окно [{p['from']}, {p['to']}] вне 0…{dur} или from > to")
    if not isinstance(entry.get("slots", {}), dict):
        errs.append("slots: объект")
    files = entry.get("files", {})
    if not isinstance(files, dict):
        errs.append("files: объект {роль: путь}")
    else:
        for role, rel in files.items():
            if not isinstance(rel, str) or not rel:
                errs.append(f"files.{role}: нужен путь-строка")
            elif Path(rel).is_absolute() or rel.startswith("~") or ".." in Path(rel).parts:
                errs.append(f"files.{role}: путь {rel!r} — только относительно библиотеки")
    return errs


def validate(index):
    """Ошибки всего индекса: записи + уникальность id."""
    errs = []
    if index.get("version") != VERSION:
        errs.append(f"version {index.get('version')!r}: ожидается {VERSION}")
    seen = set()
    for e in index.get("assets", []):
        id_ = e.get("id") if isinstance(e, dict) else None
        errs += [f"{id_}: {m}" for m in validate_entry(e)]
        if id_ in seen:
            errs.append(f"{id_}: id повторяется")
        seen.add(id_)
    return errs


def missing_files(library, entry):
    """Роли из files, чьих файлов нет на диске (предупреждение, не ошибка схемы)."""
    return [role for role, rel in (entry.get("files") or {}).items()
            if not (Path(library) / rel).exists()]


# ── правка и поиск ───────────────────────────────────────────────────────────

def get(index, id_):
    return next((e for e in index["assets"] if e.get("id") == id_), None)


def add_or_replace(index, entry):
    """Запись с тем же id заменяется на месте, новая — в конец. Невалидная — ValueError."""
    errs = validate_entry(entry)
    if errs:
        raise ValueError(f"запись {entry.get('id')!r} не годится:\n  " + "\n  ".join(errs))
    for i, e in enumerate(index["assets"]):
        if e.get("id") == entry["id"]:
            index["assets"][i] = entry
            return index
    index["assets"].append(entry)
    return index


def norm(text):
    return str(text).lower().replace("ё", "е")


def hits(entry, query):
    """Где запрос нашёлся: [(поле, текст)]. Каждое слово запроса должно найтись хоть где-то."""
    words = norm(query).split()
    fields = [("id", entry.get("id", ""))]
    fields += [("tag", t) for t in entry.get("tags", [])]
    fields.append(("describes", entry.get("describes", "")))
    fields += [("event", f"{ev['t']}: {ev['what']}") for ev in entry.get("events", [])]
    found = []
    for w in words:
        got = [(name, text) for name, text in fields if w in norm(text)]
        if not got:
            return []
        found += [g for g in got if g not in found]
    return found


WEIGHT = {"tag": 3, "id": 2, "describes": 2, "event": 1}


def find(index, query=None, kind=None, layout=None, theme=None):
    """Записи под фильтры; с запросом — по убыванию веса совпадений (теги весят больше)."""
    out = []
    for e in index["assets"]:
        if kind and e.get("kind") != kind:
            continue
        if layout and e.get("layout") != layout:
            continue
        if theme and e.get("theme") != theme:
            continue
        if query:
            h = hits(e, query)
            if not h:
                continue
            out.append((sum(WEIGHT[name] for name, _ in h), e))
        else:
            out.append((0, e))
    out.sort(key=lambda p: -p[0])    # сортировка устойчивая: при равенстве — порядок индекса
    return [e for _, e in out]


def _subtract(windows, cut):
    a, b = cut
    out = []
    for x, y in windows:
        if b <= x or a >= y:
            out.append([x, y])
            continue
        if a > x:
            out.append([x, a])
        if b < y:
            out.append([b, y])
    return out


def usable_windows(entry, min_len=0.5, pad=0.0):
    """Стоячие участки: вся длительность минус переходы и приватные окна (каждое
    расширено на pad), только куски не короче min_len. Сюда /reel ставит вставку."""
    dur = float(entry["duration"])
    wins = [[0.0, dur]]
    cuts = [list(w) for w in entry.get("transitions", []) or []]
    cuts += [[p["from"], p["to"]] for p in entry.get("private", []) or []]
    for a, b in cuts:
        wins = _subtract(wins, (max(0.0, a - pad), min(dur, b + pad)))
    return [[round(a, 2), round(b, 2)] for a, b in wins if b - a >= min_len - 1e-9]


# ── CLI ──────────────────────────────────────────────────────────────────────

def resolve_library(arg=None, settings_path=None):
    """--library, иначе folders.library из reel.settings.json автора."""
    if arg:
        return Path(arg).expanduser()
    import settings
    s = settings.load(settings_path)
    lib = s and s["folders"].get("library")
    if not lib:
        raise SystemExit("библиотека не задана: --library <папка> или "
                         "«папки.библиотека_ассетов» в reel.settings.json")
    return Path(lib)


def line(e):
    return (f"{str(e.get('id')):<28} {e.get('kind')}/{e.get('layout')}/{str(e.get('theme')):<5} "
            f"{float(e.get('duration') or 0):>5.1f} с  {e.get('describes', '')}")


def show_text(library, e):
    out = [line(e)]
    if e.get("tags"):
        out.append("  теги: " + ", ".join(e["tags"]))
    for ev in e.get("events", []):
        out.append(f"  {ev['t']:>5.2f}  {ev['what']}")
    if e.get("transitions"):
        out.append("  переходы: " + ", ".join(f"{a}–{b}" for a, b in e["transitions"]))
    for p in e.get("private", []) or []:
        out.append(f"  ПРИВАТНОЕ {p['from']}–{p['to']}: {p.get('what', '')}")
    if e.get("kind") == "broll" or e.get("transitions") or e.get("private"):
        out.append("  стоячие окна: " + ", ".join(f"{a}–{b}" for a, b in usable_windows(e)))
    for role, rel in (e.get("files") or {}).items():
        mark = "" if (Path(library) / rel).exists() else "  (нет файла)"
        out.append(f"  {role}: {rel}{mark}")
    return "\n".join(out)


def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--library", help="папка библиотеки (иначе из настроек)")
    common.add_argument("--settings", help="reel.settings.json автора")
    common.add_argument("--json", action="store_true", help="вывод JSON")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", parents=[common], help="все ассеты")
    f = sub.add_parser("find", parents=[common], help="поиск по тегам/описанию/событиям")
    f.add_argument("query", nargs="?")
    f.add_argument("--kind", choices=KINDS)
    f.add_argument("--layout", choices=LAYOUTS)
    f.add_argument("--theme", choices=THEMES)
    s = sub.add_parser("show", parents=[common], help="одна запись подробно")
    s.add_argument("id")
    sub.add_parser("validate", parents=[common], help="проверка схемы и файлов")
    a = sub.add_parser("add", parents=[common], help="добавить/заменить запись из JSON-файла")
    a.add_argument("entry_json")
    args = ap.parse_args(argv)

    lib = resolve_library(args.library, args.settings)
    index = load(lib)
    if args.cmd == "list":
        items = index["assets"]
    elif args.cmd == "find":
        items = find(index, args.query, args.kind, args.layout, args.theme)
    elif args.cmd == "show":
        e = get(index, args.id)
        if e is None:
            raise SystemExit(f"нет ассета {args.id!r} в {index_path(lib)}")
        print(json.dumps(e, ensure_ascii=False, indent=2) if args.json else show_text(lib, e))
        return 0
    elif args.cmd == "add":
        entry = json.loads(Path(args.entry_json).read_text(encoding="utf-8"))
        path = put(lib, entry)
        print(f"Записано: {entry['id']} → {path}")
        miss = missing_files(lib, entry)
        if miss:
            print("  нет файлов: " + ", ".join(miss))
        return 0
    else:  # validate
        errs = validate(index)
        warns = [f"{e.get('id')}: нет файла {r}" for e in index["assets"]
                 for r in missing_files(lib, e)]
        if args.json:
            print(json.dumps({"errors": errs, "warnings": warns}, ensure_ascii=False, indent=2))
        else:
            print(f"{index_path(lib)}: {len(index['assets'])} ассетов, "
                  f"{len(errs)} ошибок, {len(warns)} предупреждений")
            for m in errs:
                print("  ОШИБКА " + m)
            for m in warns:
                print("  внимание: " + m)
        return 1 if errs else 0

    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
    else:
        print(f"{index_path(lib)}: {len(items)}")
        for e in items:
            print(line(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
