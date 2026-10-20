"""Подписка «YouTube → Telegram» (16:9): мини-скринкаст графикой на настоящих интерфейсах. Шапка
канала YouTube по центру, курсор жмёт «Подписаться» → «Вы подписаны», кликает ссылку в шапке —
YouTube уезжает влево, справа открывается профиль канала в Telegram, курсор жмёт «Подписаться» и там.
Родная тема — светлая (фон вокруг карточек); раскладка — full.

Когда брать: «подписывайтесь на YouTube и в Telegram», «ссылка на канал — в шапке» — показать путь
подписки действием, а не пилюлей «подпишись». Снято со сцены `subscribe` ролика news-reposter
(автор 2026-10-19: «хочу переиспользовать»).

Интерфейсы повторяют настоящие тёмные темы YouTube и Telegram, поэтому их цвета свои (UI_COLORS),
а не из темы: тема даёт фон вокруг и заглушки аватаров и обложек. Данные каналов — слотами; значок
площадки — свой файл (чужих логотипов в шаблоне нет). Курсор попадает в центр кнопки по разметке,
а не по координатам на глаз. Числа подписчиков и роликов не показываются: устаревают.
"""
import _common as c
import _wide as w

NAME = "wide_follow"
TITLE = "Подписка YouTube → Telegram (16:9)"
DEFAULT_KIND = "light"
FORMAT = w.FORMAT
DEFAULT_LAYOUT = "full"
BASE_TAGS = ["подписка", "youtube", "telegram", "канал", "ссылка", "курсор"]
SLOTS = {
    "yt_name": {"about": "имя канала на YouTube", "default": "Мой канал"},
    "yt_handle": {"about": "ник без @, пусто — строки нет", "default": ""},
    "yt_about": {"about": "описание в шапке (одна строка, хвост обрежется «…ещё»)",
                 "default": "О чём канал — одной фразой"},
    "yt_link": {"about": "ссылка в шапке — по ней клик и переход", "default": "ссылка на канал"},
    "yt_more": {"about": "приписка после ссылки, например «и ещё 1 ссылка»; можно пусто", "default": ""},
    "yt_avatar": {"about": "аватар канала: путь к картинке; пусто — кружок с буквой", "default": ""},
    "yt_logo": {"about": "значок площадки над шапкой: свой SVG/PNG; пусто — без значка", "default": ""},
    "yt_logo_text": {"about": "подпись рядом со значком; пусто — без подписи", "default": ""},
    "videos": {"about": "до 3 роликов {image, title}; пусто — заглушки темы, [] с grid=false — без сетки",
               "default": []},
    "grid": {"about": "вкладки «Видео / Shorts» и ролики под шапкой", "default": True},
    "tg_title": {"about": "название канала в Telegram", "default": "Мой канал"},
    "tg_handle": {"about": "ник без @, пусто — только «канал»", "default": ""},
    "tg_about": {"about": "текст «информация» в профиле", "default": "О чём канал — одной-двумя фразами."},
    "tg_avatar": {"about": "аватар канала в Telegram: путь к картинке; пусто — кружок с буквой", "default": ""},
    "at": {"about": "секунда появления шапки YouTube", "default": 0.2},
    "yt_at": {"about": "клик «Подписаться» на YouTube (0 — через 1,3 с)", "default": 0},
    "link_at": {"about": "клик по ссылке в шапке (0 — через 1 с после подписки)", "default": 0},
    "tg_at": {"about": "клик «Подписаться» в Telegram (0 — через 1,5 с после ссылки)", "default": 0},
    "duration": {"about": "длина, с (0 — последний клик + 1,6 с)", "default": 0},
    "tags": {"about": "доп. теги", "default": []},
}

YT = {"bg": "#0F0F0F", "text": "#F1F1F1", "muted": "#AAAAAA", "link": "#3EA6FF", "done": "#272727", "line": "#3F3F3F"}
TG = {"bg": "#1C1C1E", "muted": "#8E8E93", "btn": "#3E88F7", "tile": "#26272D", "link": "#5EB5F7", "line": "#3A3A3F"}
UI_COLORS = {v.upper() for v in [*YT.values(), *TG.values()]}       # тест: неизменные с темой цвета — только эти
YT_X, CH_X, TOP, YT_W, CH_W, SLIDE = 450, 1150, 170, 1020, 700, 380

CURSOR = ('<svg viewBox="0 0 28 28" width="46" height="46"><path d="M5 2 L5 23 L10.5 18 L14.5 26.5 L18 25 L14 16.5 L21.5 16.5 Z" '
          'fill="#000000" stroke="#FFFFFF" stroke-width="2" stroke-linejoin="round"/></svg>')
FLOW_JS = """const click = (sel, at) => { tl.to(sel, { scale: 0.86, duration: 0.07 }, at); tl.to(sel, { scale: 1, duration: 0.1 }, at + 0.07); };
// кончик стрелки — в центр элемента по разметке (offsetLeft/Top: без GSAP-сдвигов), а не по ручным координатам
const center = (sel) => { let el = document.querySelector(sel), x = el.offsetWidth / 2, y = el.offsetHeight / 2;
  while (el) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; } return [x, y]; };
const cursorTo = (sel, at, d = 0.5) => { const [x, y] = center(sel); tl.to("#cur", { x: x - 8, y: y - 3, duration: d, ease: "power2.inOut" }, at); };"""
TAP, CLICKED, WHOOSH, SWISH = ("tap", -9.0), ("select", -14.0), ("whoosh", -13.0), ("swish", -15.0)


def avatar(value, name, letter_of, cls):
    """Аватар: картинка из слота или кружок с первой буквой имени. → (html, files)."""
    html, files = c.icon_html(value or (letter_of.strip()[:1].upper() or "•"), "", name=name)
    return f'<div class="{cls}">{html}</div>', files


def yt_html(s):
    files = []
    head = ""
    if s["yt_logo"] or s["yt_logo_text"]:
        lg, f = c.icon_html(s["yt_logo"], "lg", name="yt-logo") if s["yt_logo"] else ("", [])
        files += f
        tx = f'<b class="lgt">{c.esc(s["yt_logo_text"])}</b>' if s["yt_logo_text"] else ""
        head = f'<div class="lgr">{lg}{tx}</div>'
    av, f = avatar(s["yt_avatar"], "yt-avatar", s["yt_name"], "yav")
    files += f
    handle = f'<div class="yh">@{c.esc(s["yt_handle"])}</div>' if s["yt_handle"] else ""
    more = f' <b class="yt">{c.esc(s["yt_more"])}</b>' if s["yt_more"] else ""
    chevron = (f'<svg width="16" height="10" viewBox="0 0 16 10"><path d="M2 2 L8 8 L14 2" fill="none" stroke="{YT["text"]}" '
               f'stroke-width="2.4" stroke-linecap="round"/></svg>')
    grid = ""
    if s["grid"]:
        vids = list(s["videos"])[:3] or [{"title": f"Ролик {i + 1}"} for i in range(3)]
        cells = []
        for i, v in enumerate(vids):
            if v.get("image"):
                im, f = c.icon_html(v["image"], "th", name=f"yt-video{i}")
                files += f
            else:
                im = '<div class="th ph"></div>'
            cells.append(f'<div class="vc">{im}<div class="vt">{c.esc(v.get("title", ""))}</div></div>')
        grid = (f'<div class="tabs"><span class="on">Видео</span><span>Shorts</span></div>'
                f'<div class="vids">{"".join(cells)}</div>')
    html = (f'<div class="pf" id="yt" style="left:{YT_X}px; top:{TOP}px; width:{YT_W}px">{head}'
            f'<div class="yr">{av}<div style="min-width:0"><div class="yn">{c.esc(s["yt_name"])}</div>{handle}'
            f'<div class="ya"><span class="yat">{c.esc(s["yt_about"])}</span><b class="yt">…ещё</b></div>'
            f'<div class="yl"><span id="ytl">{c.esc(s["yt_link"])}</span>{more}</div>'
            f'<div class="bw" style="width:250px"><div class="yb" id="ytb">Подписаться</div>'
            f'<div class="yd" id="ytd">🔔 Вы подписаны{chevron}</div></div></div></div>{grid}</div>')
    return html, files


def ch_html(s):
    av, files = avatar(s["tg_avatar"], "tg-avatar", s["tg_title"], "cav")
    sub = "канал" + (f' · @{c.esc(s["tg_handle"])}' if s["tg_handle"] else "")
    link = (f'<div class="cs"></div><div class="cm" style="font-size:20px">ссылка</div>'
            f'<div class="cl">@{c.esc(s["tg_handle"])}</div>') if s["tg_handle"] else ""
    tiles = "".join(f'<div class="ct"><span>{i}</span>{t}</div>' for i, t in (("💬", "Чат"), ("🔔", "Звук"), ("•••", "Ещё")))
    html = (f'<div class="pf" id="ch" style="left:{CH_X}px; top:{TOP}px; width:{CH_W}px">{av}'
            f'<div class="cn">{c.esc(s["tg_title"])}</div><div class="cm">{sub}</div>'
            f'<div class="bw" style="height:64px; margin-top:24px"><div class="cb" id="chb">ПОДПИСАТЬСЯ</div>'
            f'<div class="cd" id="chd">{tiles}</div></div>'
            f'<div class="ci"><div class="cl" style="font-size:20px">информация</div><div class="cx">{c.esc(s["tg_about"])}</div>{link}</div></div>')
    return html, files


def build(slots, theme, kind=None, layout=None):
    layout = layout or DEFAULT_LAYOUT
    s = c.merge_slots(SLOTS, slots)
    pal = c.palette(theme, kind or DEFAULT_KIND)
    b0, b1 = w.blues(pal)
    yt, f1 = yt_html(s)
    ch, f2 = ch_html(s)
    content = yt + ch + f'<div id="cur" class="cur">{CURSOR}</div>'
    at = float(s["at"])
    t_yt = float(s["yt_at"]) or at + 1.3
    t_link = float(s["link_at"]) or t_yt + 1.0
    t_tg = float(s["tg_at"]) or t_link + 1.5
    if not at < t_yt < t_link < t_tg:
        raise ValueError(f"порядок кликов: at {at} < yt_at {t_yt} < link_at {t_link} < tg_at {t_tg}")
    end = float(s["duration"]) or t_tg + 1.6
    dur = end + w.EXIT + w.TAIL
    t_slide = t_link + 0.12
    f = c.fmt
    js = [FLOW_JS, f'popIn("#yt", {f(at)}, 0.35);', 'tl.set("#cur", { x: 952, y: 1037 }, 0);',
          f'fadeIn("#cur", {f(max(at + 0.2, t_yt - 0.9))});',
          f'cursorTo("#ytb", {f(max(at + 0.3, t_yt - 0.8))}, {f(min(0.7, max(0.35, t_yt - at - 0.4)))});',
          f'click("#cur", {f(t_yt)});', f'fadeIn("#ytd", {f(t_yt + 0.05)}, 0.15);',
          f'tl.to("#ytb", {{ opacity: 0, duration: 0.1 }}, {f(t_yt + 0.05)});',
          f'cursorTo("#ytl", {f(t_yt + 0.15)}, {f(max(0.3, t_link - t_yt - 0.2))});', f'click("#cur", {f(t_link)});',
          f'tl.to("#ytl", {{ backgroundColor: "{c.rgba(YT["link"], 0.25)}", duration: 0.12 }}, {f(t_link)});',
          f'tl.to("#yt", {{ x: -{SLIDE}, duration: 0.5, ease: "power3.inOut" }}, {f(t_slide)});',
          f'tl.to("#cur", {{ x: "-={SLIDE}", duration: 0.5, ease: "power3.inOut" }}, {f(t_slide)});',
          f'tl.fromTo("#ch", {{ opacity: 0, x: 120, scale: 0.96 }}, {{ opacity: 1, x: 0, scale: 1, duration: 0.45, ease: "power3.out" }}, {f(t_slide + 0.2)});',
          f'cursorTo("#chb", {f(t_slide + 0.5)}, {f(max(0.3, t_tg - t_slide - 0.6))});', f'click("#cur", {f(t_tg)});',
          f'fadeIn("#chd", {f(t_tg + 0.05)}, 0.15);', f'tl.to("#chb", {{ opacity: 0, duration: 0.1 }}, {f(t_tg + 0.05)});',
          f'tl.to("#cur", {{ opacity: 0, duration: 0.2 }}, {f(min(end - 0.1, t_tg + 0.6))});',
          f'groupOut("#yt, #ch", {f(end)});']
    events = [c.ev(at, f"шапка канала YouTube «{s['yt_name']}» проявляется"),
              c.ev(t_yt, "курсор жмёт «Подписаться» → «Вы подписаны»"),
              c.ev(t_link, f"клик по ссылке в шапке «{s['yt_link']}»"),
              c.ev(t_slide + 0.2, f"YouTube уезжает влево, справа — канал в Telegram «{s['tg_title']}»"),
              c.ev(t_tg, "курсор жмёт «Подписаться» в Telegram"),
              c.ev(end, "обе карточки уходят размытием")]
    sfx = [w.cue(at, WHOOSH), w.cue(t_yt, TAP), w.cue(t_yt + 0.08, CLICKED), w.cue(t_link, TAP), w.cue(t_slide, SWISH),
           w.cue(t_tg, TAP), w.cue(t_tg + 0.08, CLICKED), w.cue(end, w.SWISH)]
    body, bg, size = w.compose(pal, layout, content)
    style = w.css(pal, layout) + f"""
.pf {{ position: absolute; border-radius: 24px; overflow: hidden; opacity: 0; color: {c.WHITE};
  font-family: -apple-system, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif;
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.28), 0 0 0 1px rgba(0, 0, 0, 0.06); }}
#yt {{ background: {YT['bg']}; padding: 26px 40px 34px; }}
#ch {{ background: {TG['bg']}; padding: 34px 34px 30px; text-align: center; }}
.lgr {{ display: flex; align-items: center; gap: 8px; height: 34px; margin-bottom: 26px; }}
.lgr .lg {{ height: 34px; width: auto; }}
.lgt {{ font-size: 29px; letter-spacing: -0.04em; color: {YT['text']}; }}
.yr {{ display: flex; gap: 34px; align-items: center; }}
.yav, .cav {{ flex: none; border-radius: 50%; overflow: hidden; background: linear-gradient(135deg, {b0}, {b1});
  color: {c.WHITE}; display: flex; align-items: center; justify-content: center; font-weight: 800; }}
.yav {{ width: 190px; height: 190px; font-size: 84px; }}
.cav {{ width: 170px; height: 170px; font-size: 76px; margin: 0 auto; }}
.yav img, .cav img {{ width: 100%; height: 100%; object-fit: cover; }}
.yn {{ font-size: 54px; font-weight: 800; color: {YT['text']}; letter-spacing: -0.01em; }}
.yh {{ font-size: 24px; color: {YT['text']}; margin-top: 8px; font-weight: 600; }}
.ya {{ display: flex; font-size: 22px; color: {YT['muted']}; margin-top: 10px; white-space: nowrap; }}
.yat {{ min-width: 0; overflow: hidden; }}
.ya b {{ flex: none; margin-left: 6px; }}
.yt {{ color: {YT['text']}; }}
.yl {{ font-size: 22px; color: {YT['link']}; margin-top: 8px; }}
#ytl {{ display: inline-block; border-radius: 6px; padding: 0 4px; margin: 0 -4px; }}
.bw {{ position: relative; height: 58px; margin-top: 20px; }}
.yb, .yd {{ position: absolute; inset: 0; border-radius: 999px; display: flex; align-items: center; justify-content: center;
  font-size: 25px; font-weight: 700; white-space: nowrap; }}
.yb {{ background: {YT['text']}; color: {YT['bg']}; }}
.yd {{ background: {YT['done']}; color: {YT['text']}; gap: 10px; opacity: 0; font-size: 24px; }}
.tabs {{ display: flex; gap: 34px; font-size: 24px; font-weight: 700; margin: 30px 0 0; border-bottom: 1px solid {YT['line']}; color: {YT['muted']}; }}
.tabs span {{ padding-bottom: 12px; }}
.tabs .on {{ color: {YT['text']}; border-bottom: 3px solid {YT['text']}; }}
.vids {{ display: flex; gap: 18px; margin-top: 22px; }}
.vc {{ flex: 1; min-width: 0; }}
.th {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 14px; display: block; }}
.th.ph {{ background: linear-gradient(135deg, {b0}, {b1}); }}
.vt {{ font-size: 21px; color: {YT['text']}; font-weight: 600; margin-top: 10px; line-height: 1.25; height: 52px; overflow: hidden; }}
.cn {{ font-size: 31px; font-weight: 700; margin-top: 18px; line-height: 1.25; }}
.cm {{ font-size: 22px; color: {TG['muted']}; margin-top: 6px; }}
.cb {{ position: absolute; inset: 0; background: {TG['btn']}; border-radius: 16px; display: flex; align-items: center;
  justify-content: center; font-size: 25px; font-weight: 700; letter-spacing: 0.04em; }}
.cd {{ position: absolute; inset: 0; display: flex; gap: 14px; opacity: 0; }}
.ct {{ flex: 1; background: {TG['tile']}; border-radius: 16px; display: flex; align-items: center; justify-content: center; gap: 8px;
  color: {TG['link']}; font-size: 22px; font-weight: 600; }}
.ct span {{ font-size: 24px; line-height: 1; }}
.ci {{ background: {TG['tile']}; border-radius: 20px; padding: 20px 24px; margin-top: 22px; text-align: left; }}
.cl {{ font-size: 23px; color: {TG['link']}; }}
.cx {{ font-size: 23px; line-height: 1.35; margin-top: 6px; }}
.cs {{ height: 1px; background: {TG['line']}; margin: 16px 0 12px; }}
.cur {{ position: absolute; left: 0; top: 0; opacity: 0; z-index: 50; }}
"""
    describes = f"подписка: YouTube «{s['yt_name']}» → ссылка в шапке → Telegram «{s['tg_title']}», курсор жмёт «Подписаться» дважды"
    return w.result(style, body, js, dur, events, pal, layout, bg, size, f1 + f2, BASE_TAGS + list(s["tags"]),
                    describes, preview_t=t_tg + 0.4, sfx=sfx)
