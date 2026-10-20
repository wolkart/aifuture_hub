#!/usr/bin/env python3
"""Каталог приёмов: index.json библиотеки → страница-сетка с постоянными номерами. Только stdlib.

  catalog.py build [--out <папка>]            — собрать страницу
  catalog.py serve [--port 8765] [--host …]   — пересобрать и отдать библиотеку по HTTP
  catalog.py deploy-help [--port 8765]        — как вынести каталог на свой сервер без домена
  общие флаги: --library <папка> (иначе папки.библиотека_ассетов из reel.settings.json), --settings

Страница — <библиотека>/_каталог/index.html (+ data.json, posters/): карточки с крупным номером,
названием, длительностью, раскладкой, «когда брать» и тегами; поиск и фильтры-чипы; клик по
карточке — видео играет без звука по кругу, второй клик — пауза. Всё inline, без CDN: страница
открывается с сервера по IP без интернета и просто файлом.

Номер приёма постоянный и живёт в <библиотека>/_каталог/numbers.json, а не в index.json:
library.add_or_replace заменяет запись целиком, и перерендер сцены стёр бы поле. Новый ассет
получает следующий номер в порядке index.json, номер удалённого не переиспользуется.

Видео — относительными путями от страницы (../<id>/<id>.mp4): страница живёт внутри библиотеки,
сервер отдаёт папку библиотеки. Оверлей без mp4 (.mov с альфой, зелёный) в браузере не играет —
у него кадр и подпись. Постеры — уменьшенные кадры в _каталог/posters/ (ffmpeg; нет его —
превью как есть). «Когда брать» у сцены — колонка из references/templates.md, у б-ролла —
слова-теги, по которым его берёт /reel: ничего не сочиняется.
"""
import argparse
import concurrent.futures
import functools
import http.server
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import library  # noqa: E402

CATALOG = "_каталог"
NUMBERS = "numbers.json"
TEMPLATES = HERE.parent / "templates"
TEMPLATES_DOC = HERE.parent / "references" / "templates.md"
POSTER_BOX = (600, 750)     # кадр карточки 4:5 на ретине
TITLE_MAX = 72
PORT = 8765
FILE_LABELS = {"mp4": "mp4", "mov_alpha": "mov с альфой", "green": "зелёный", "sfx": "звук",
               "preview": "кадр", "project": "проект"}


# ── номера ───────────────────────────────────────────────────────────────────

def numbers_path(lib):
    return Path(lib) / CATALOG / NUMBERS


def load_numbers(path):
    p = Path(path)
    if not p.exists():
        return {"version": 1, "next": 1, "numbers": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("numbers", {})
    data.setdefault("next", 1)
    return data


def assign_numbers(ids, numbers):
    """Номера по порядку ids: у известных — прежние, новым — следующие свободные.
    Номер удалённого ассета не переиспользуется. → (numbers, [новые id])."""
    nums = dict(numbers.get("numbers") or {})
    nxt = max([int(numbers.get("next") or 1)] + [n + 1 for n in nums.values()])
    added = []
    for id_ in ids:
        if id_ not in nums:
            nums[id_] = nxt
            nxt += 1
            added.append(id_)
    return {"version": 1, "next": nxt, "numbers": nums}, added


def write_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


# ── тексты карточки ──────────────────────────────────────────────────────────

def template_info(templates_dir=TEMPLATES, doc=TEMPLATES_DOC):
    """{шаблон: {title, when}}: TITLE модуля (читается текстом — модули не импортируем) и
    колонка «Когда брать» из references/templates.md."""
    info = {}
    for p in sorted(Path(templates_dir).glob("*.py")):
        if p.stem.startswith("_"):
            continue
        m = re.search(r'^TITLE\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"), re.M)
        info[p.stem] = {"title": m.group(1) if m else p.stem, "when": ""}
    doc = Path(doc)
    if doc.exists():
        for row in doc.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*`(\w+)`", row)
            if not m:
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            when = re.sub(r"[`*]", "", cells[-1]).strip()
            info.setdefault(m.group(1), {"title": m.group(1), "when": ""})["when"] = when
    return info


def split_describes(text):
    """«что в кадре» → (название, остальное): режем по первому «:», «;» или «,» вне скобок и
    кавычек-ёлочек. Слишком длинное название — по слову с многоточием, остальное — всё.
    Заглавная — только у обычного слова: домен и путь остаются как есть."""
    text = " ".join(str(text or "").split())
    head, rest = text, ""
    depth = 0
    for i, ch in enumerate(text):
        if ch in "(«":
            depth += 1
        elif ch in ")»":
            depth = max(0, depth - 1)
        elif depth == 0 and ch in ":;," and text[:i].strip():
            head, rest = text[:i].strip(), text[i + 1:].strip()
            break
    if len(head) > TITLE_MAX:
        head, rest = head[:TITLE_MAX].rsplit(" ", 1)[0].rstrip(",:;—- ") + "…", text
    if re.fullmatch(r"[^\W\d_][\w-]*", head.split(" ", 1)[0]) and head[:1].islower():
        head = head[0].upper() + head[1:]    # «rea.tools/…», «github.com» — как есть
    return head, rest


def when_text(entry, tpl):
    """«Когда брать»: строка шаблона из каталога, иначе слова-теги (по ним ассет берёт /reel)."""
    if tpl and tpl.get("when"):
        return tpl["when"]
    tags = [t for t in entry.get("tags") or [] if str(t).strip()]
    return ("на словах " + ", ".join(f"«{t}»" for t in tags[:4])) if tags else ""


def sec(x):
    return f"{float(x):.1f}".replace(".", ",")


# ── медиа ────────────────────────────────────────────────────────────────────

def media_files(lib, entry):
    """→ (видео для браузера, превью, файл без браузера: .mov/зелёный) — пути от библиотеки."""
    id_, files = entry["id"], entry.get("files") or {}

    def first(*rels):
        return next((r for r in rels if r and (Path(lib) / r).is_file()), None)

    video = first(files.get("mp4"), f"{id_}/{id_}.mp4")
    preview = first(files.get("preview"), f"{id_}/{id_}-preview.png")
    other = first(files.get("mov_alpha"), f"{id_}/{id_}.mov",
                  files.get("green"), f"{id_}/{id_}-green.mp4")
    return video, preview, other


def has_ffmpeg():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def probe_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip()
    w, h = out.split("x")[:2]
    return int(w), int(h)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    return None


def make_poster(src, dst, at=None):
    """Уменьшенный кадр в рамку карточки; свежий — не пересобирается."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    w, h = POSTER_BOX
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if at:
        cmd += ["-ss", f"{at:.2f}"]
    cmd += ["-i", str(src), "-frames:v", "1", "-vf",
            f"scale=w={w}:h={h}:force_original_aspect_ratio=decrease:force_divisible_by=2"]
    if dst.suffix == ".jpg":
        cmd += ["-q:v", "4"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd + [str(dst)], check=True, capture_output=True)
    return True


def prepare_media(lib, out, entry, use_ffmpeg):
    """Файлы ассета + постер + размер кадра. → dict для карточки."""
    lib = Path(lib)
    video, preview, other = media_files(lib, entry)
    alpha = entry.get("layout") == "overlay" or entry.get("kind") == "overlay"
    poster_file = Path(out) / "posters" / f"{entry['id']}.{'png' if alpha else 'jpg'}"
    src = preview or video or other
    made, dims = False, None
    if use_ffmpeg and src:
        try:
            at = None if preview else round(float(entry.get("duration") or 0) / 2, 2)
            made = make_poster(lib / src, poster_file, at)
        except (subprocess.CalledProcessError, OSError):
            pass
        try:
            dims = probe_size(lib / (video or other or preview))
        except (subprocess.CalledProcessError, OSError, ValueError):
            pass
    if dims is None and preview:
        dims = png_size(lib / preview)
    poster = poster_file if poster_file.exists() else None
    return {"video": video, "preview": preview, "other": other, "poster": poster,
            "made": made, "dims": dims}


def frame_format(dims, entry):
    if dims:
        w, h = dims
        return "16:9" if w > h * 1.5 else "9:16"
    return "16:9" if str(entry.get("template") or "").startswith("wide_") else "9:16"


def rel_url(out, path):
    """Путь на диске → относительная ссылка от страницы, с %-кодированием (кириллица, пробелы)."""
    rel = os.path.relpath(Path(path), Path(out))
    return quote(Path(rel).as_posix(), safe="/")


# ── сборка ───────────────────────────────────────────────────────────────────

def card(lib, out, entry, no, tpl_info, media):
    lib = Path(lib)
    tpl = tpl_info.get(entry.get("template") or "")
    title, about = split_describes(entry.get("describes") or "")
    if not title:
        title, about = (tpl["title"] if tpl else entry["id"]), ""
    kind = entry.get("kind")
    if media["video"]:
        note = ""
    elif media["other"]:
        note = "оверлей с альфой: в браузере только кадр, в монтажку — .mov"
    else:
        note = "видеофайла нет на диске"
    poster = (rel_url(out, media["poster"]) if media["poster"]
              else rel_url(out, lib / media["preview"]) if media["preview"] else None)
    files = [{"label": FILE_LABELS.get(role, role), "url": rel_url(out, lib / rel)}
             for role, rel in (entry.get("files") or {}).items()
             if isinstance(rel, str) and (lib / rel).is_file()]
    if not files and media["video"]:
        files = [{"label": "mp4", "url": rel_url(out, lib / media["video"])}]
    return {
        "no": no,
        "id": entry["id"],
        "title": title,
        "about": about,
        "kind": kind,
        "layout": entry.get("layout"),
        "theme": entry.get("theme"),
        "format": frame_format(media["dims"], entry),
        "duration": float(entry.get("duration") or 0),
        "template": tpl["title"] if tpl else "",
        "group": tpl["title"] if tpl else ("свой б-ролл" if kind == "broll" else "без шаблона"),
        "when": when_text(entry, tpl),
        "tags": [str(t) for t in entry.get("tags") or []],
        "events": [{"t": ev["t"], "what": ev["what"]} for ev in entry.get("events") or []
                   if isinstance(ev, dict) and "t" in ev and ev.get("what")],
        "private": [f"{sec(p['from'])}–{sec(p['to'])} с: {p.get('what', '')}".rstrip(": ")
                    for p in entry.get("private") or [] if isinstance(p, dict) and "from" in p],
        "video": rel_url(out, lib / media["video"]) if media["video"] else None,
        "poster": poster,
        "note": note,
        "files": files,
    }


def build(lib, out=None, use_ffmpeg=None, tpl_info=None, workers=6):
    """Собрать каталог. → {html, data, items, added, posters_made}."""
    lib = Path(lib)
    out = Path(out) if out else lib / CATALOG
    out.mkdir(parents=True, exist_ok=True)
    if use_ffmpeg is None:
        use_ffmpeg = has_ffmpeg()
    tpl_info = template_info() if tpl_info is None else tpl_info

    index = library.load(lib)
    entries = [e for e in index["assets"] if isinstance(e, dict) and e.get("id")]
    numbers, added = assign_numbers([e["id"] for e in entries], load_numbers(numbers_path(lib)))
    write_json(numbers_path(lib), numbers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        medias = list(pool.map(lambda e: prepare_media(lib, out, e, use_ffmpeg), entries))
    items = [card(lib, out, e, numbers["numbers"][e["id"]], tpl_info, m)
             for e, m in zip(entries, medias)]
    items.sort(key=lambda a: a["no"])
    data = {"version": 1, "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "library": lib.name, "count": len(items), "assets": items}
    write_json(out / "data.json", data)
    html = out / "index.html"
    html.write_text(render_html(data), encoding="utf-8")
    return {"html": html, "data": out / "data.json", "items": items, "added": added,
            "posters_made": sum(m["made"] for m in medias), "ffmpeg": use_ffmpeg}


def report(res, numbers_file):
    items = res["items"]
    playable = sum(1 for a in items if a["video"])
    lines = [f"Каталог: {res['html']} · ассетов {len(items)}"]
    if res["added"]:
        nums = sorted(a["no"] for a in items if a["id"] in set(res["added"]))
        span = f"№{nums[0]}" if len(nums) == 1 else f"№{nums[0]}–{nums[-1]}"
        lines.append(f"Новые номера: {len(nums)} ({span}) → {numbers_file}")
    else:
        lines.append(f"Новых номеров нет → {numbers_file}")
    lines.append(f"Видео: {playable} играет в браузере · {len(items) - playable} только кадр")
    lines.append(f"Постеры: новых {res['posters_made']}" if res["ffmpeg"]
                 else "Постеры: ffmpeg нет — превью как есть")
    return "\n".join(lines)


# ── сервер ───────────────────────────────────────────────────────────────────

def byte_range(header, size):
    """Заголовок Range → (start, end) включительно; False — диапазон вне файла (416);
    None — не разобрали (несколько диапазонов, мусор) — отдаём файл целиком."""
    m = re.fullmatch(r"\s*bytes\s*=\s*(\d*)\s*-\s*(\d*)\s*", header or "")
    if not m or not (m.group(1) or m.group(2)):
        return None
    if m.group(1):
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
        if start >= size:
            return False
        if end < start:
            return None
        return start, min(end, size - 1)
    suffix = int(m.group(2))
    if suffix == 0 or size == 0:
        return False
    return max(0, size - suffix), size - 1


class _Part:
    """Кусок открытого файла длиной n — для copyfile."""

    def __init__(self, f, n):
        self.f, self.left = f, n

    def read(self, size=-1):
        if self.left <= 0:
            return b""
        size = self.left if size is None or size < 0 else min(size, self.left)
        data = self.f.read(size)
        self.left -= len(data)
        return data

    def close(self):
        self.f.close()


class Handler(http.server.SimpleHTTPRequestHandler):
    """Статика библиотеки + Range: без него видео не перематывается, а Safari не играет вовсе.
    Списки папок не отдаём; корень ведёт на каталог."""

    def send_head(self):
        if urlsplit(self.path).path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/" + quote(CATALOG) + "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        size = os.path.getsize(path)
        span = byte_range(rng, size)
        if span is None:
            return super().send_head()
        if span is False:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        start, end = span
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Last-Modified", self.date_time_string(int(os.path.getmtime(path))))
        self.end_headers()
        return _Part(f, end - start + 1)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass    # браузер оборвал загрузку видео при перемотке — норма

    def log_request(self, code="-", size="-"):
        if isinstance(code, int) and code >= 400:
            super().log_request(code, size)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def make_server(lib, host="127.0.0.1", port=PORT):
    return Server((host, port), functools.partial(Handler, directory=str(lib)))


def lan_ip():
    """Адрес машины в сети (пакет никуда не уходит — UDP без отправки)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return None


# ── выкладка ─────────────────────────────────────────────────────────────────

DEPLOY_HELP = """\
Каталог на свой сервер без домена — доступ по IP

Ниже IP — адрес сервера, user — твой пользователь там, /srv/motion — куда положить библиотеку.
Скрипт сам ничего на сервер не копирует и по ssh не ходит: команды — для тебя.

1. Собери каталог здесь (кадры-постеры делает ffmpeg; на сервере он не нужен):
     python3 {script} build
2. Перенеси библиотеку вместе с _каталог/ (повторный запуск докачивает только новое):
     rsync -avz --progress "{lib}/" user@IP:/srv/motion/
   Не хочешь везти лишнее — добавь --exclude '_референсы' --exclude '_профили'.

Вариант А — nginx (Range и кэш из коробки, пароль парой строк):
     sudo apt install nginx apache2-utils
     sudo htpasswd -c /etc/nginx/motion.htpasswd user          # спросит пароль
   /etc/nginx/sites-available/motion:
     server {{
       listen {port};
       root /srv/motion;
       charset utf-8;
       autoindex off;
       auth_basic "motion";
       auth_basic_user_file /etc/nginx/motion.htpasswd;
       location = / {{ return 302 /_каталог/; }}
       location / {{ try_files $uri $uri/ =404; }}
       location ~ /\\. {{ deny all; }}
     }}
     sudo ln -s /etc/nginx/sites-available/motion /etc/nginx/sites-enabled/
     sudo nginx -t && sudo systemctl reload nginx
     sudo ufw allow {port}/tcp                                  # если включён ufw
   → http://IP:{port}/_каталог/

Вариант Б — этот скрипт под systemd (без nginx и без пароля):
   на сервере нужны python3 и клон хаба (catalog.py берёт library.py рядом).
   /etc/systemd/system/motion-catalog.service:
     [Unit]
     Description=Каталог моушн-приёмов
     After=network.target

     [Service]
     User=user
     ExecStart=/usr/bin/python3 /opt/aifuture_hub/skills/motion-assets/scripts/catalog.py serve --host 0.0.0.0 --port {port} --library /srv/motion
     Restart=on-failure

     [Install]
     WantedBy=multi-user.target
     sudo systemctl daemon-reload && sudo systemctl enable --now motion-catalog
     sudo ufw allow {port}/tcp
   → http://IP:{port}/_каталог/

ВНИМАНИЕ: без пароля страница публичная. Кто узнает IP и порт — увидит каталог и скачает видео,
а по прямой ссылке получит любой файл библиотеки: index.json, _референсы/, _профили/. Закрыть:
  • пароль nginx (вариант А) — по голому http он идёт открытым текстом: для личного каталога
    терпимо, для ценного нужен https, а для него домен;
  • или serve только на 127.0.0.1 (без --host 0.0.0.0, порт в ufw не открывать) и SSH-туннель:
      ssh -N -L {port}:127.0.0.1:{port} user@IP     → http://localhost:{port}/_каталог/

Обновить: build здесь → тот же rsync. Номера живут в _каталог/numbers.json — веди библиотеку
в одном месте (здесь), на сервер только копируй, иначе номера разъедутся.
"""


# ── страница ─────────────────────────────────────────────────────────────────

PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Каталог приёмов</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%232a62f0'/%3E%3Cpath d='M12 9v14l11-7z' fill='white'/%3E%3C/svg%3E">
<style>
:root {
  color-scheme: light dark;
  --bg: #f3f4f6; --grid: rgba(20, 30, 50, .045); --surface: #fff; --ink: #14161b; --ink-2: #555c68;
  --ink-3: #8a909b; --line: #e2e5ea; --accent: #2a62f0; --accent-soft: #e7eefe; --chip: #fff;
  --chip-on: #14161b; --chip-on-ink: #fff; --media: #e6e8ec; --warn: #b4410c; --warn-soft: #fdf0e7;
  --shadow: 0 1px 2px rgba(16, 24, 40, .05), 0 8px 24px rgba(16, 24, 40, .07);
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0e1014; --grid: rgba(255, 255, 255, .03); --surface: #171a20; --ink: #eceef2; --ink-2: #a5abb6;
    --ink-3: #757b86; --line: #272b33; --accent: #7ea4ff; --accent-soft: #1b2540; --chip: #1c1f26;
    --chip-on: #eceef2; --chip-on-ink: #0e1014; --media: #0a0b0e; --warn: #f59a5b; --warn-soft: #2a1a10;
    --shadow: 0 1px 2px rgba(0, 0, 0, .4), 0 10px 28px rgba(0, 0, 0, .35);
  }
}
* { box-sizing: border-box; }
[hidden] { display: none !important; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background-color: var(--bg); color: var(--ink); font: 15px/1.45 var(--sans);
  background-image: linear-gradient(var(--grid) 1px, transparent 1px),
                    linear-gradient(90deg, var(--grid) 1px, transparent 1px);
  background-size: 28px 28px;
}
.wrap { max-width: 1440px; margin: 0 auto; padding: 0 24px; }
button { font: inherit; color: inherit; }
.mono { font-family: var(--mono); }

/* шапка */
header.top { padding-top: 28px; padding-bottom: 8px; }
.head-row { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
h1 { margin: 0; font-size: 28px; letter-spacing: -.02em; line-height: 1.1; }
.count { color: var(--ink-3); font: 13px var(--mono); }
.spacer { flex: 1; }
.sort { font: 13px var(--sans); color: var(--ink-2); background: var(--chip); border: 1px solid var(--line);
        border-radius: 10px; padding: 7px 10px; }
.searchbar { position: sticky; top: 0; z-index: 5; padding: 12px 0; background: linear-gradient(var(--bg) 70%, transparent); }
.search { display: flex; align-items: center; gap: 10px; background: var(--surface); border: 1px solid var(--line);
          border-radius: 14px; padding: 0 14px; box-shadow: var(--shadow); }
.search svg { flex: none; color: var(--ink-3); }
.search input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--ink);
                font: 16px var(--sans); padding: 13px 0; }
.search kbd { font: 12px var(--mono); color: var(--ink-3); border: 1px solid var(--line); border-radius: 6px; padding: 1px 6px; }
.filters { display: grid; gap: 8px; padding: 4px 0 18px; }
.group { display: grid; grid-template-columns: 86px 1fr; align-items: start; gap: 6px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.glabel { font: 12px/26px var(--mono); color: var(--ink-3); }
.chip { border: 1px solid var(--line); background: var(--chip); border-radius: 999px; padding: 4px 11px;
        font-size: 13px; cursor: pointer; line-height: 1.3; }
.chip i { font-style: normal; color: var(--ink-3); font: 11px var(--mono); margin-left: 4px; }
.chip[aria-pressed="true"] { background: var(--chip-on); color: var(--chip-on-ink); border-color: var(--chip-on); }
.chip[aria-pressed="true"] i { color: inherit; opacity: .7; }
.chip:disabled { opacity: .35; cursor: default; }
.chip.more { border-style: dashed; color: var(--ink-2); }
.reset { border: 0; background: none; color: var(--accent); cursor: pointer; font-size: 13px; padding: 4px 6px; }

/* сетка */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 22px; padding-bottom: 40px; }
.card { background: var(--surface); border-radius: 18px; box-shadow: var(--shadow); overflow: hidden;
        display: flex; flex-direction: column; cursor: pointer; scroll-margin-top: 90px; }
.card.flash { outline: 3px solid var(--accent); outline-offset: 3px; }
.media { position: relative; aspect-ratio: 4 / 5; background: var(--media); overflow: hidden; outline: 0; }
.media:focus-visible { box-shadow: inset 0 0 0 3px var(--accent); }
.media .fill { position: absolute; inset: -12%; width: 124%; height: 124%; object-fit: cover;
               filter: blur(22px) saturate(1.15); opacity: .55; }
.media video, .media .still { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.media.alpha { background-color: #d9dce1;
  background-image: conic-gradient(#c3c7ce 25%, transparent 0 50%, #c3c7ce 0 75%, transparent 0);
  background-size: 18px 18px; }
.play { position: absolute; left: 50%; top: 50%; width: 56px; height: 56px; margin: -28px 0 0 -28px;
        border-radius: 50%; background: rgba(10, 12, 16, .55); color: #fff; display: grid; place-items: center;
        backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); transition: opacity .15s, transform .15s; pointer-events: none; }
.card:hover .play { transform: scale(1.06); }
.card.playing .play { opacity: 0; }
.dur { position: absolute; right: 10px; bottom: 10px; background: rgba(10, 12, 16, .72); color: #fff;
       font: 12px var(--mono); padding: 3px 7px; border-radius: 7px; }
.badge { position: absolute; left: 10px; top: 10px; background: rgba(10, 12, 16, .72); color: #fff;
         font: 11px var(--mono); padding: 3px 7px; border-radius: 7px; }
.note { position: absolute; left: 10px; right: 10px; bottom: 44px; background: rgba(10, 12, 16, .72); color: #fff;
        font-size: 12px; line-height: 1.35; padding: 6px 9px; border-radius: 9px; text-align: center; }
.body { padding: 14px 16px 16px; display: flex; flex-direction: column; gap: 7px; flex: 1; }
.title-row { display: flex; gap: 10px; align-items: flex-start; }
.no { flex: none; font: 700 22px/1 var(--mono); color: var(--accent); background: var(--accent-soft);
      border-radius: 9px; padding: 6px 8px 5px; letter-spacing: -.03em; }
.no small { font-size: 14px; opacity: .75; margin-right: 2px; }
h2 { margin: 2px 0 0; font-size: 16px; line-height: 1.25; letter-spacing: -.01em; }
.about { margin: 0; color: var(--ink-2); font-size: 13px; display: -webkit-box; -webkit-line-clamp: 3;
         -webkit-box-orient: vertical; overflow: hidden; }
.when { margin: 0; font-size: 13px; }
.when b { font-weight: 600; }
.warn { margin: 0; font-size: 12.5px; color: var(--warn); background: var(--warn-soft); border-radius: 8px; padding: 4px 8px; }
.meta { font: 11.5px/1.5 var(--mono); color: var(--ink-3); }
.meta b { color: var(--ink-2); font-weight: 500; }
.tags { display: flex; flex-wrap: wrap; gap: 4px; }
.tag { border: 0; background: var(--bg); color: var(--ink-2); border-radius: 6px; padding: 2px 7px; font-size: 12px; cursor: pointer; }
.tag:hover, .tag.on { background: var(--accent-soft); color: var(--accent); }
details.ev { font-size: 12.5px; }
details.ev summary { cursor: pointer; color: var(--ink-3); font: 12px var(--mono); list-style: none; }
details.ev summary::-webkit-details-marker { display: none; }
details.ev summary::before { content: "▸ "; }
details.ev[open] summary::before { content: "▾ "; }
details.ev ol { list-style: none; margin: 6px 0 0; padding: 0; display: grid; gap: 2px; }
details.ev li { display: flex; gap: 8px; align-items: baseline; border-radius: 6px; padding: 1px 4px; }
details.ev li.now { background: var(--accent-soft); }
details.ev button { border: 0; background: none; padding: 0; color: var(--accent); cursor: pointer; font: 12px var(--mono); flex: none; min-width: 52px; text-align: left; }
.files { font: 11.5px var(--mono); color: var(--ink-3); margin-top: auto; padding-top: 4px; display: flex; flex-wrap: wrap; gap: 4px 10px; }
.files a { color: var(--ink-2); text-decoration: none; border-bottom: 1px solid var(--line); }
.files a:hover { color: var(--accent); border-color: var(--accent); }
.empty { text-align: center; color: var(--ink-2); padding: 60px 0; }
footer { color: var(--ink-3); font: 12px var(--mono); padding: 10px 24px 40px; }

@media (max-width: 640px) {
  .wrap { padding: 0 16px; }
  header.top { padding-top: 20px; }
  .group { grid-template-columns: 1fr; gap: 4px; }
  .glabel { line-height: 1.4; }
  h1 { font-size: 23px; }
  .grid { gap: 16px; }
}
@media (prefers-reduced-motion: reduce) { .play { transition: none; } }
</style>
</head>
<body>
<header class="top wrap">
  <div class="head-row">
    <h1>Каталог приёмов</h1>
    <span class="count" id="count"></span>
    <span class="spacer"></span>
    <select class="sort" id="sort" aria-label="Порядок">
      <option value="no">по номеру</option>
      <option value="new">новые сверху</option>
      <option value="short">короткие сначала</option>
      <option value="long">длинные сначала</option>
    </select>
  </div>
</header>
<div class="searchbar"><div class="wrap">
  <label class="search">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="q" type="search" placeholder="Номер, слово, тег, событие…" autocomplete="off" aria-label="Поиск">
    <kbd>/</kbd>
  </label>
</div></div>
<div class="wrap"><div class="filters" id="filters"></div></div>
<main class="wrap">
  <div class="grid" id="grid"></div>
  <div class="empty" id="empty" hidden>Ничего не нашлось. <button class="reset" id="reset2">Сбросить фильтры</button></div>
</main>
<footer id="foot"></footer>
<script id="data" type="application/json">__DATA__</script>
<script>
(() => {
  const DATA = JSON.parse(document.getElementById('data').textContent);
  const A = DATA.assets;
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const norm = s => String(s).toLowerCase().replace(/ё/g, 'е');
  const sec = x => (Math.round(x * 10) / 10).toFixed(1).replace('.', ',');
  const at = x => String(Math.round(x * 100) / 100).replace('.', ',');   // таймкод события: 0,15
  const plural = (n, one, few, many) => {
    const m10 = n % 10, m100 = n % 100;
    return m10 === 1 && m100 !== 11 ? one : m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14) ? few : many;
  };
  const RU = {
    kind: { scene: 'сцена', broll: 'б-ролл', overlay: 'оверлей' },
    layout: { full: 'весь экран', half: 'половина', overlay: 'оверлей' },
    theme: { dark: 'тёмная', light: 'светлая' },
  };
  const GROUPS = [
    { key: 'kind', label: 'тип', get: a => [a.kind] },
    { key: 'layout', label: 'раскладка', get: a => [a.layout] },
    { key: 'format', label: 'формат', get: a => [a.format] },
    { key: 'theme', label: 'тема', get: a => [a.theme] },
    { key: 'group', label: 'приём', get: a => [a.group] },
    { key: 'tag', label: 'теги', get: a => a.tags, top: 16 },
  ];
  const name = (key, v) => (RU[key] && RU[key][v]) || v;
  const sel = Object.fromEntries(GROUPS.map(g => [g.key, new Set()]));
  let query = '', tagsOpen = false, current = null;

  A.forEach(a => {
    a.hay = norm(['№' + a.no, a.id, a.title, a.about, a.group, a.when, a.tags.join(' '),
                  a.events.map(e => e.what).join(' ')].join(' '));
  });

  // ── карточки ──
  function buildCard(a) {
    const card = el('article', 'card');
    card.id = 'n' + a.no;
    const media = el('div', 'media' + (a.kind === 'overlay' || a.layout === 'overlay' ? ' alpha' : ''));
    media.tabIndex = 0;
    media.setAttribute('role', 'button');
    media.setAttribute('aria-label', 'Играть №' + a.no);
    if (a.poster && a.layout !== 'overlay') {
      const fill = el('img', 'fill');
      fill.src = a.poster; fill.alt = ''; fill.loading = 'lazy'; fill.setAttribute('aria-hidden', 'true');
      media.append(fill);
    }
    if (a.video) {
      const v = el('video');
      v.muted = true; v.loop = true; v.playsInline = true;
      v.setAttribute('muted', ''); v.setAttribute('playsinline', '');
      if (a.poster) { v.poster = a.poster; v.preload = 'none'; v.src = a.video; }
      else { v.preload = 'metadata'; v.src = a.video + '#t=0.1'; }
      v.addEventListener('play', () => card.classList.add('playing'));
      v.addEventListener('pause', () => card.classList.remove('playing'));
      v.addEventListener('timeupdate', () => markEvent(card, v.currentTime));
      media.append(v);
      const play = el('span', 'play');
      play.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.6-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5Z"/></svg>';
      media.append(play);
    } else if (a.poster) {
      const img = el('img', 'still');
      img.src = a.poster; img.alt = a.title; img.loading = 'lazy';
      media.append(img);
    }
    if (a.note) media.append(el('span', 'note', a.note));
    media.append(el('span', 'badge', name('layout', a.layout) + ' · ' + a.format));
    media.append(el('span', 'dur', sec(a.duration) + ' с'));
    card.append(media);

    const body = el('div', 'body');
    const row = el('div', 'title-row');
    const no = el('span', 'no mono');
    no.append(el('small', '', '№'), document.createTextNode(a.no));
    row.append(no, el('h2', '', a.title));
    body.append(row);
    if (a.about) body.append(el('p', 'about', a.about));
    if (a.when) {
      const w = el('p', 'when');
      w.append(el('b', '', 'Когда брать: '), document.createTextNode(a.when));
      body.append(w);
    }
    a.private.forEach(p => body.append(el('p', 'warn', 'Приватное, не брать: ' + p)));
    const meta = el('div', 'meta');
    meta.append(el('b', '', name('kind', a.kind)),
      document.createTextNode(' · ' + name('layout', a.layout) + ' · ' + name('theme', a.theme) +
        ' · ' + a.format + (a.template ? ' · ' + a.template : '')));
    body.append(meta);
    if (a.tags.length) {
      const tags = el('div', 'tags');
      a.tags.forEach(t => {
        const b = el('button', 'tag', '#' + t);
        b.type = 'button'; b.dataset.tag = t;
        b.addEventListener('click', () => { toggleSel('tag', t); });
        tags.append(b);
      });
      body.append(tags);
    }
    if (a.events.length) {
      const d = el('details', 'ev');
      d.append(el('summary', '', 'опись · ' + a.events.length + ' ' + plural(a.events.length, 'событие', 'события', 'событий')));
      const ol = el('ol');
      a.events.forEach(e => {
        const li = el('li');
        li.dataset.t = e.t;
        const b = el('button', '', at(e.t) + ' с');
        b.type = 'button';
        b.addEventListener('click', () => seek(card, e.t));
        li.append(b, document.createTextNode(e.what));
        ol.append(li);
      });
      d.append(ol);
      body.append(d);
    }
    const files = el('div', 'files');
    files.append(el('span', '', a.id));
    a.files.forEach(f => {
      const l = el('a', '', f.label);
      l.href = f.url; l.target = '_blank'; l.rel = 'noopener';
      files.append(l);
    });
    body.append(files);
    card.append(body);

    card.addEventListener('click', e => {
      if (e.target.closest('a, button, summary, details, input, select')) return;
      toggle(card);
    });
    media.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(card); }
    });
    return card;
  }

  function toggle(card) {
    const v = $('video', card);
    if (!v) return;
    if (v.paused) {
      if (current && current !== v) current.pause();
      current = v;
      v.play().catch(() => {});
    } else v.pause();
  }
  function seek(card, t) {
    const v = $('video', card);
    if (!v) return;
    if (current && current !== v) current.pause();
    current = v;
    const go = () => { v.currentTime = t; v.play().catch(() => {}); };
    if (v.readyState >= 1) go(); else { v.preload = 'auto'; v.addEventListener('loadedmetadata', go, { once: true }); v.load(); }
  }
  function markEvent(card, t) {
    const d = $('details.ev', card);
    if (!d || !d.open) return;
    let last = null;
    d.querySelectorAll('li').forEach(li => { li.classList.remove('now'); if (+li.dataset.t <= t + 0.05) last = li; });
    if (last) last.classList.add('now');
  }

  const cards = new Map(A.map(a => [a.no, buildCard(a)]));

  // ── фильтры ──
  const qwords = () => norm(query).split(/\s+/).filter(Boolean);
  function match(a, skip) {
    const q = query.trim();
    const num = q.match(/^№?\s*(\d+)$/);
    if (num) { if (a.no !== +num[1]) return false; }
    else if (q && !qwords().every(w => a.hay.includes(w))) return false;
    for (const g of GROUPS) {
      if (g.key === skip) continue;
      const s = sel[g.key];
      if (s.size && !g.get(a).some(v => s.has(v))) return false;
    }
    return true;
  }
  function toggleSel(key, v) {
    const s = sel[key];
    s.has(v) ? s.delete(v) : s.add(v);
    update();
  }
  function values(g) {
    const c = new Map();
    A.forEach(a => g.get(a).forEach(v => c.set(v, (c.get(v) || 0) + 1)));
    return [...c.entries()].sort((x, y) => y[1] - x[1] || String(x[0]).localeCompare(String(y[0]), 'ru'));
  }
  function renderFilters() {
    const box = $('#filters');
    box.textContent = '';
    GROUPS.forEach(g => {
      let vals = values(g);
      if (vals.length < 2) return;
      const facet = new Map();
      A.forEach(a => { if (match(a, g.key)) g.get(a).forEach(v => facet.set(v, (facet.get(v) || 0) + 1)); });
      const row = el('div', 'group');
      const chips = el('div', 'chips');
      row.append(el('span', 'glabel', g.label), chips);
      let hidden = 0;
      if (g.top && !tagsOpen && vals.length > g.top) {
        hidden = vals.length - g.top;
        vals = vals.filter(([v], i) => i < g.top || sel[g.key].has(v));
      }
      vals.forEach(([v]) => {
        const b = el('button', 'chip', name(g.key, v));
        b.type = 'button';
        const n = facet.get(v) || 0;
        b.append(el('i', '', n));
        b.setAttribute('aria-pressed', sel[g.key].has(v));
        if (!n && !sel[g.key].has(v)) b.disabled = true;
        b.addEventListener('click', () => toggleSel(g.key, v));
        chips.append(b);
      });
      if (g.top && vals.length > g.top || hidden) {
        const more = el('button', 'chip more', tagsOpen ? 'свернуть' : 'ещё ' + hidden);
        more.type = 'button';
        more.addEventListener('click', () => { tagsOpen = !tagsOpen; renderFilters(); });
        chips.append(more);
      }
      box.append(row);
    });
    const any = query.trim() || GROUPS.some(g => sel[g.key].size);
    if (any) {
      const r = el('button', 'reset', 'сбросить всё');
      r.type = 'button';
      r.addEventListener('click', reset);
      box.append(r);
    }
  }
  const SORTS = {
    no: (x, y) => x.no - y.no,
    new: (x, y) => y.no - x.no,
    short: (x, y) => x.duration - y.duration || x.no - y.no,
    long: (x, y) => y.duration - x.duration || x.no - y.no,
  };
  function update() {
    const grid = $('#grid');
    const order = [...A].sort(SORTS[$('#sort').value] || SORTS.no);
    const same = order.every((a, i) => grid.children[i] === cards.get(a.no));
    let shown = 0;
    order.forEach(a => {
      const c = cards.get(a.no);
      const ok = match(a);
      c.hidden = !ok;
      if (!ok) { const v = $('video', c); if (v && !v.paused) v.pause(); }
      shown += ok;
      if (!same) grid.append(c);
      c.querySelectorAll('.tag').forEach(t => t.classList.toggle('on', sel.tag.has(t.dataset.tag)));
    });
    $('#count').textContent = shown === A.length
      ? A.length + ' ' + plural(A.length, 'приём', 'приёма', 'приёмов')
      : 'показано ' + shown + ' из ' + A.length;
    $('#empty').hidden = shown > 0;
    renderFilters();
  }
  function reset() {
    query = ''; $('#q').value = '';
    GROUPS.forEach(g => sel[g.key].clear());
    update();
  }

  $('#q').addEventListener('input', e => { query = e.target.value; update(); });
  $('#q').addEventListener('keydown', e => { if (e.key === 'Escape') { e.target.value = ''; query = ''; update(); } });
  $('#sort').addEventListener('change', update);
  $('#reset2').addEventListener('click', reset);
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== $('#q')) { e.preventDefault(); $('#q').focus(); }
  });
  $('#foot').textContent = 'собран ' + DATA.built + ' · ' + DATA.library + ' · ' + A.length + ' ' +
    plural(A.length, 'ассет', 'ассета', 'ассетов') + ' · номер постоянный: ссылка на приём — #n<номер>';
  update();

  const m = location.hash.match(/^#n(\d+)$/);
  if (m && cards.has(+m[1])) {
    const c = cards.get(+m[1]);
    c.scrollIntoView({ block: 'center' });
    c.classList.add('flash');
    setTimeout(() => c.classList.remove('flash'), 1600);
  }
})();
</script>
</body>
</html>
"""


def render_html(data):
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    return PAGE.replace("__DATA__", payload)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv=None):
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--library", help="папка библиотеки (иначе из настроек)")
    common.add_argument("--settings", help="reel.settings.json автора")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", parents=[common], help="собрать страницу каталога")
    b.add_argument("--out", help=f"папка страницы (по умолчанию <библиотека>/{CATALOG})")
    b.add_argument("--no-ffmpeg", action="store_true", help="без постеров и замера кадра")
    s = sub.add_parser("serve", parents=[common], help="пересобрать и отдать библиотеку по HTTP")
    s.add_argument("--host", default="127.0.0.1", help="0.0.0.0 — доступ из сети (по IP)")
    s.add_argument("--port", type=int, default=PORT)
    d = sub.add_parser("deploy-help", parents=[common], help="как вынести каталог на свой сервер")
    d.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)

    if args.cmd == "deploy-help":
        try:
            lib = library.resolve_library(args.library, args.settings)
        except SystemExit:
            lib = "<библиотека>"
        print(DEPLOY_HELP.format(script=Path(__file__).resolve(), lib=lib, port=args.port))
        return 0

    lib = library.resolve_library(args.library, args.settings)
    if not library.index_path(lib).exists():
        raise SystemExit(f"нет {library.index_path(lib)} — это не папка библиотеки")
    out = Path(args.out).expanduser() if args.cmd == "build" and args.out else None
    res = build(lib, out, use_ffmpeg=False if getattr(args, "no_ffmpeg", False) else None)
    print(report(res, numbers_path(lib)))
    if args.cmd == "build":
        return 0

    try:
        server = make_server(lib, args.host, args.port)
    except OSError as e:
        raise SystemExit(f"порт {args.port} не открылся ({e.strerror}) — возьми другой: --port <N>")
    port = server.server_address[1]
    path = "/" + quote(CATALOG) + "/"
    print(f"Каталог: http://localhost:{port}/{CATALOG}/")
    if args.host not in ("127.0.0.1", "localhost"):
        ip = lan_ip()
        print(f"По сети: http://{ip or '<IP>'}:{port}{path}  ← без пароля, см. deploy-help")
    print("Остановить: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
