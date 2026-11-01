"""Сцены ролика — образец. Лежит в export/монтаж/scenes.py; собирает build.py, проверяет check.py.

Снято с пробного куска news-reposter (5 мин экспорта FocuSee, 2026-10-20): номера фраз — из
отчёта резки (longform.py lines / words.json), поэтому в другом ролике сцены пишутся заново. Здесь
по одной сцене каждого вида:
  Д — сцена-действие на весь кадр (Ins "full"): мини-скринкаст графикой, настоящие интерфейсы;
  Э — поверх экрана (Ins "over"): прозрачный клип, вуаль, экран и запись под ним живые;
  П — панель wide_drawer (drawer): автор уезжает влево, группы по словам;
  А — акцент у головы (Tpl wide_chips / wide_number / wide_message / wide_list): оверлей поверх зума.

Время — всегда словами: at(фраза, слово) — секунда таймлайна, s.t(фраза, слово) — от начала сцены.
Слово — номер или начало слова («одной», «копир»). Правила ремесла — references/scene-craft.md.
"""
from stage import *  # noqa: F401,F403


# ── Д · «Устанавливается это одной командой… копируете… бесплатно» ─────────────

def install():
    s = Ins("install", at(15, "одной") - 0.3, "full", what="«1 команда» → GitHub → терминал → бот, бесплатно")
    t_one, copy_at, free_at = s.t(15, "одной"), s.t(16, "копируете"), s.t(17, "бесплатно")
    t_win = max(t_one + 1.2, copy_at - 1.3)
    cmd = "curl -fsSL https://raw.githubusercontent.com/wolkart/news-reposter/main/install.sh | bash"
    t_type0 = copy_at + 0.45
    t_type1 = max(t_type0 + 0.5, min(copy_at + 1.7, free_at - 0.75))
    end = s.t(18, 0, 0, -0.7)                           # впритык к панели: она выезжает за 0,4 с до фразы 18, хвост 0,3
    s.style(".big { font-size: 300px; } .ln { opacity: 0; } #caret { opacity: 0; }")
    s.add(f'<div class="abs" style="left:0; right:0; top:330px; text-align:center"><div class="big" id="one" style="position:relative; display:inline-block">'
          f'<span style="color:{SEC}">1</span> команда</div></div>', "one")
    s.add(window("gh", 80, 210, 860,
                 f'<div style="display:flex; align-items:center; gap:14px; padding:22px 28px; border-bottom:1px solid #E7E9EE">{ico("github-color.svg", 38)}'
                 f'<div style="font-size:32px; color:#57606A">wolkart / <b style="color:#1F2328">news-reposter</b></div></div>'
                 f'<div style="padding:30px 34px 36px"><div style="font-size:44px; font-weight:700; color:#1F2328">Быстрый способ — одна команда</div>'
                 f'<div class="mono" style="position:relative; margin-top:20px; background:#F6F8FA; border:1px solid #E7E9EE; border-radius:14px; '
                 f'padding:22px 80px 22px 22px; font-size:27px; color:#1F2328; line-height:1.45; word-break:break-all">{cmd}'
                 f'<div id="cp" style="position:absolute; right:16px; top:16px; width:46px; height:46px; border-radius:10px; border:1px solid #D0D7DE; '
                 f'background:#fff; display:flex; align-items:center; justify-content:center; font-size:24px">⧉</div></div>'
                 f'<div class="pill" id="copied" style="position:relative; margin-top:20px; font-size:30px; padding:12px 24px; color:{OK}">✓ Скопировано</div>'
                 f'</div>', "github.com"), "gh")
    lines = ["✓ Docker уже стоит", "Скачиваю код…", "✓ Скачано"]
    out_lines = "".join(f'<div class="ln" id="l{i}" style="color:{"#7EE2A8" if t.startswith("✓") else "#C9CCD6"}">{t}</div>' for i, t in enumerate(lines))
    s.add(term("term", 980, 150, 880,
               f'<div style="word-break:break-all"><span style="color:#7EE2A8">root@server</span>:~# {typed(cmd)}<span id="caret" style="background:#E6E6EA">&nbsp;</span></div>'
               f'<div style="margin-top:16px">{out_lines}<div class="ln" id="lok" style="color:#7EE2A8; font-weight:700">✓ Готово. Открой бота → /start</div></div>',
               "root@server — 120×30", h=700), "term")
    s.add(window("bot", 1150, 720, 680,
                 f'<div style="display:flex; align-items:center; gap:18px; padding:22px 26px"><div style="width:74px;height:74px;border-radius:50%;'
                 f'background:linear-gradient(135deg,#6FB3FF,#2F7DE1);color:#fff;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:700">A</div>'
                 f'<div style="flex:1"><div style="font-size:30px;font-weight:700;color:#1F2328">AI News Reposter</div>'
                 f'<div style="font-size:22px;color:#8A8F98">бот · переписывает и постит новости</div></div>{ico("telegram-color.svg", 52)}</div>'), "bot")
    s.add(pill("free", 1560, 640, "Бесплатно", 32, f"background:linear-gradient(135deg,{SEC},#3F5FC2); color:#fff"), "free")
    s.add(pill("tagai", 180, 880, "🤖 AI-бот", 36), "tagai")
    s.add(pill("tagauto", 470, 880, "⚙️ автоматизация", 36), "tagauto")

    s.pop("#one", t_one, "reward", -13, 0.3).out("#one", t_win - 0.15)
    s.pop("#gh", t_win, "swish", -16, 0.35).pop("#term", t_win + 0.15, None, d=0.35)
    s.cursor(520, 980, copy_at - 0.9).cursor_to("#cp", copy_at - 0.75, 0.65)       # курсор — в центр кнопки «копировать»
    s.pop("#copied", copy_at + 0.05, "pop", -15, 0.22)
    s.code(f'moveTo("#cur", {f(copy_at + 0.2)}, 1300, 330, 0.35);').fade("#caret", t_type0 - 0.1, 0.05)
    s.type(len(cmd), t_type0, t_type1 - t_type0).out("#cur", t_type1 + 0.1).out("#caret", t_type1 + 0.05, 0.05)   # команда ушла — каретки нет
    span = max(0.4, free_at - 0.25 - t_type1)
    for i in range(len(lines)):
        s.fade(f"#l{i}", t_type1 + 0.08 + span * i / len(lines), 0.1)
    s.fade("#lok", free_at - 0.15, 0.12).sound(free_at - 0.05, "reward", -14)
    s.pop("#bot", free_at).pop("#free", free_at + 0.12)
    s.pop("#tagai", s.t(17, "ai") - 0.1, "pop", -16).pop("#tagauto", s.t(17, "автоматиз") - 0.1, "pop", -16)
    s.mark("#bot", s.t(17, "сервис"))                   # пауза 2 с между «бесплатно» и «AI» (build.py --gaps)
    return s.done(end)


# ── П · «В видео расскажу… инструкцию… обещал подписчикам Telegram… на YouTube» ──

def video_plan():
    return drawer("p-video", at(18, 0) - 0.4, at(22, last(22), 1) + 0.4, [
        {"at": at(18, 0), "type": "list", "rubric": "В этом видео", "title": "Что *покажу*", "items": [
            {"icon": "🛠", "title": "Как я это сделал", "sub": "", "at": at(18, "сделал")},
            {"icon": "⚡", "title": "Почему сейчас это просто", "sub": "", "at": at(19, "прикольно")},
            {"icon": "📘", "title": "Инструкция по установке", "sub": "", "at": at(20, "инструкцию")}]},
        {"at": at(21, 0), "type": "message", "rubric": "Обещал подписчикам", "name": "Подписчик", "avatar": "П", "time": "в канале",
         "text": "Сделаешь инструкцию по установке?", "reply": "Держите — целым роликом на YouTube", "reply_at": at(22, "youtube")},
    ], what="что в ролике → подписчик просил инструкцию → «держите, целым роликом»")


# ── А · «…того же Claude Code… через Open Code… Deepseek Harness» — чипы у головы ──

def tools():
    s0 = at(73, "claude") - 1.2
    end = at(75, "deepseek") + 2.2                       # последний чип побудет на экране (check.py: «мелькнуло»)
    return Tpl("tools", "wide_chips", s0, {
        "items": [{"icon": logo_path("claude-code-mascot.svg"), "label": "Claude Code", "at": at(73, "claude")},
                  {"icon": "</>", "label": "Open Code", "at": at(75, "open")},
                  {"icon": logo_path("deepseek-color.svg"), "label": "DeepSeek Harness", "at": at(75, "deepseek")}],
        "head": [0.48, 0.47], "spread": 0.2, "duration": round(end - s0, 3)}, what="Claude Code / Open Code / DeepSeek Harness у головы")


# ── Э · экран стоит, автор объясняет: «сервис на коде гибче, в n8n — костыли» ─────

def flexible():
    s = Ins("flexible", at(79, 0) - 0.3, "over", what="код гибче ✓ / n8n — костыли ✕ (поверх висящего экрана)")
    t_code, t_flex, t_n8n, t_crutch = s.t(79, "переписал"), s.t(80, "гибче"), s.t(80, "n8n"), s.t(80, "костыли")
    end = s.t(81, 0, 0, -0.15)                           # дальше автор показывает Excalidraw — экран открываем
    card = ('<div class="win ui" id="{id}" style="left:110px; top:{y}px; width:900px; background:#fff; border-radius:28px; padding:30px 36px">'
            '<div style="display:flex; align-items:center; gap:20px">{icon}<div style="font-size:44px; font-weight:800; color:{ink}">{title}</div></div>'
            '<div class="pill" id="{id}v" style="position:relative; margin-top:22px; font-size:34px; {extra}">{verdict}</div></div>')
    s.add(card.format(id="cd", y=170, ink=INK, icon='<span style="font-size:56px">&lt;/&gt;</span>', title="Сервис на коде",
                      verdict="✓ гибче — что угодно под задачу", extra=f"color:{OK}"), "cd")
    s.add(card.format(id="nn", y=560, ink=INK, icon=ico("n8n-color.svg", 64), title="Тот же сервис в n8n",
                      verdict="🩼 свои костыли", extra=f"color:{DANGER}"), "nn")
    s.pop("#cd", t_code - 0.1, "swish", -16, 0.3).pop("#cdv", t_flex - 0.1, "select", -12)
    s.pop("#nn", t_n8n - 0.1, "swish", -16, 0.3).pop("#nnv", t_crutch - 0.1).shake("#nn", t_crutch + 0.1)
    s.mark("#cd", s.t(79, "код")).mark("#cd", s.t(80, "намного"))       # паузы — пульс того, о чём речь
    s.mark("#cdv", s.t(80, "чем")).mark("#nn", s.t(80, "потому")).mark("#nn", s.t(80, "сделать"))
    return s.done(end)


SCENES = [install, video_plan, tools, flexible]
