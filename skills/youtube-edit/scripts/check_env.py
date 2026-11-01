#!/usr/bin/env python3
"""Доктор: всё ли есть для конвейера длинного ролика. Только stdlib. Ничего не ставит.

  python3 check_env.py [--settings reel.settings.json] [--json]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1]
sys.path.insert(0, str(SKILLS / "reel" / "scripts"))
import settings as settings_mod  # noqa: E402

MIN_FREE_GB = 20     # клипы графики, куски таймлайна, кадры рендера HyperFrames


def tool(name, hint):
    return {"name": name, "ok": bool(shutil.which(name)), "hint": hint}


def env_key(path, key):
    p = Path(path)
    if os.environ.get(key):
        return True
    return p.exists() and any(line.strip().startswith(f"{key}=") and line.split("=", 1)[1].strip()
                              for line in p.read_text(encoding="utf-8").splitlines())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--settings")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    checks = [tool("ffmpeg", "brew install ffmpeg"), tool("ffprobe", "ставится с ffmpeg"),
              tool("node", "brew install node (HyperFrames — рендер графики)"), tool("npx", "ставится с node"),
              tool("uv", "brew install uv (скрипты с numpy)")]
    if sys.platform == "darwin":
        checks.append(tool("swiftc", "xcode-select --install (лицо — Apple Vision: голова в кадре, точка зума)"))
    missing = [c for c in checks if not c["ok"]]
    sp = settings_mod.find(a.settings)
    sp = sp if sp and Path(sp).exists() else None
    raw = json.loads(Path(sp).read_text(encoding="utf-8")) if sp else {}
    yt = raw.get("ютуб") or {}
    free = shutil.disk_usage(Path.home()).free / 2 ** 30
    res = {
        "missing": [{"name": c["name"], "hint": c["hint"]} for c in missing],
        "settings": str(sp) if sp else None,
        "youtube_section": bool(yt),
        "music": {k: (v or {}).get("трек") for k, v in (yt.get("музыка") or {}).items()},
        "probes": len(yt.get("пробы_музыки") or []),
        "scribe_key": env_key(SKILLS / "rough-cut" / ".env", "ELEVENLABS_API_KEY"),
        "free_gb": round(free, 1),
    }
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    print("инструменты: " + ("всё на месте" if not missing else "нет " + ", ".join(f"{c['name']} ({c['hint']})" for c in missing)))
    print(f"настройки: {res['settings'] or 'нет reel.settings.json — тема нейтральная; спроси минимум (references/settings.md)'}")
    if sp and not yt:
        print("  раздела «ютуб» нет — музыка и пробы по умолчанию; образец — assets/settings.example.json")
    if yt:
        mus = ", ".join(k + " — " + (Path(v).name if v else "по пробам") for k, v in res["music"].items()) or "не задана"
        print(f"  музыка: {mus}; треков для проб: {res['probes']}")
    print(f"Scribe (дословная расшифровка с «э-м»): {'ключ есть' if res['scribe_key'] else 'ключа нет — Whisper, часть «э-м» пропустится'}")
    print(f"диск: свободно {free:.0f} ГБ" + (f" — мало (нужно ≥ {MIN_FREE_GB}): прозрачные вставки (--alpha) не включать" if free < MIN_FREE_GB else ""))


if __name__ == "__main__":
    main()
