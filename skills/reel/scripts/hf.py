"""HyperFrames: каркас страницы, проект слоя, рендер. Только stdlib.

Движок — HyperFrames (HTML + GSAP → видео), но HTML свой: каталоговые стили
субтитров латинские и заточены под 16:9. Шрифты — локальные @font-face из темы
автора (с кириллицей), семейства в CSS — var(--main) и var(--display).

Правила, без которых рендер ломается (рендер перематывает таймлайн покадрово):
  • анимировать только transform/opacity/filter/цвет; top/left линтер запрещает;
  • fromTo для элементов с CSS-трансформом; никаких tl.call с подменой текста;
  • селекторы по id; один #root с data-composition-id;
  • длительность — из реального файла (ffprobe), не из констант.
Подробнее — references/hyperframes.md.
"""
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

HF_VERSION = "0.8.150"      # обновление — осознанно: версия влияет на рендер
GSAP_VERSION = "3.15.0"
W, H, FPS = 1080, 1920, 30
CACHE = Path.home() / ".cache" / "reel"

HEAD = """<!doctype html>
<html lang="ru"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=%W%, height=%H%" />
<script src="assets/gsap.min.js"></script>
<style>
%FONTS%
:root { --main: "ReelMain", "Montserrat", "Helvetica Neue", Arial, sans-serif;
        --display: "ReelDisplay", "Oswald", "Arial Narrow", sans-serif; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: %W%px; height: %H%px; overflow: hidden; background: %BG%; }
body { font-family: var(--main); color: #fff; }
.clip { position: absolute; inset: 0; }
%CSS%
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="%DUR%" data-width="%W%" data-height="%H%" data-fps="%FPS%">
%BODY%
</div>
<script>
window.__timelines = window.__timelines || {};
const tl = gsap.timeline({ paused: true });
%JS%
window.__timelines["main"] = tl;
</script></body></html>
"""


def font_faces(fonts):
    """fonts: {"main": "main.ttf"|None, "display": …} — имена файлов в assets/."""
    out = []
    for fam, fname in (("ReelMain", fonts.get("main")), ("ReelDisplay", fonts.get("display"))):
        if fname:
            out.append(f'@font-face {{ font-family: "{fam}"; src: url("assets/{fname}"); '
                       f'font-weight: 100 900; }}')
    return "\n".join(out)


def page(css, body, js, dur, fonts=None, bg="transparent", w=W, h=H, fps=FPS):
    return (HEAD.replace("%FONTS%", font_faces(fonts or {})).replace("%CSS%", css)
            .replace("%BODY%", body).replace("%JS%", js).replace("%BG%", bg)
            .replace("%DUR%", f"{dur:.3f}").replace("%W%", str(w)).replace("%H%", str(h))
            .replace("%FPS%", str(fps)))


def clip(id_, start, end, inner, track, cls="", style=""):
    st = f' style="{style}"' if style else ""
    cls_attr = f"clip {cls}".strip()
    return (f'<div id="{id_}" class="{cls_attr}" data-start="{start:.3f}" '
            f'data-duration="{end - start:.3f}" data-track-index="{track}"{st}>{inner}</div>')


def ensure_gsap():
    """gsap.min.js нужной версии в кеше; первый раз — из npm (npm pack, без установки)."""
    dst = CACHE / f"gsap-{GSAP_VERSION}.min.js"
    if dst.exists():
        return dst
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(["npm", "pack", f"gsap@{GSAP_VERSION}", "--pack-destination", str(tmp)],
                   check=True, capture_output=True)
    tgz = next(tmp.glob("gsap-*.tgz"))
    with tarfile.open(tgz) as tf:
        member = tf.getmember("package/dist/gsap.min.js")
        with tf.extractfile(member) as src:
            dst.write_bytes(src.read())
    shutil.rmtree(tmp, ignore_errors=True)
    return dst


def setup_project(project_dir, theme, extra=()):
    """Папка слоя: assets/ с GSAP и шрифтами темы. extra — [(src, имя)] файлов рядом с
    index.html (видео для слоя). Возвращает {"main": имя|None, "display": имя|None}."""
    d = Path(project_dir)
    (d / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(ensure_gsap(), d / "assets" / "gsap.min.js")
    fonts = {}
    for key, src in (("main", theme.get("font_main")), ("display", theme.get("font_display"))):
        if src and Path(src).exists():
            name = f"{key}{Path(src).suffix.lower()}"
            shutil.copy(src, d / "assets" / name)
            fonts[key] = name
        else:
            fonts[key] = None
    for src, name in extra:
        target = d / name
        if not target.exists() or target.stat().st_size != Path(src).stat().st_size:
            shutil.copy(src, target)
    return fonts


def render_cmd(project_dir, out, fmt="mp4", quality=None, fps=FPS):
    cmd = ["npx", "--yes", f"hyperframes@{HF_VERSION}", "render", str(project_dir),
           "--output", str(out), "--fps", str(fps), "--format", fmt]
    if quality:
        cmd += ["--quality", quality]
    return cmd


def render(project_dir, out, fmt="mp4", quality=None):
    subprocess.run(render_cmd(project_dir, out, fmt, quality), check=True)
    return Path(out)


def duration(path):
    """Длительность файла по ffprobe (композиция берёт её, а не константу)."""
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(path)])
    return float(out)


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return ", ".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))
