#!/usr/bin/env python3
"""Доктор rough-cut: что есть, чего не хватает, как поставить. Только stdlib."""
import argparse
import json
import platform
import shutil
import sys

INSTALL = {
    "darwin": {"ffmpeg": "brew install ffmpeg", "uv": "brew install uv"},
    "linux": {"ffmpeg": "sudo apt install ffmpeg",
              "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh"},
    "win32": {"ffmpeg": "winget install Gyan.FFmpeg",
              "uv": "winget install astral-sh.uv"},
}


def os_key(plat=sys.platform):
    if plat.startswith("linux"):
        return "linux"
    return plat if plat in INSTALL else "linux"


def whisper_backend(plat=sys.platform, machine=platform.machine()):
    """mlx-whisper только на Apple Silicon, иначе кроссплатформенный faster-whisper."""
    return "mlx-whisper" if plat == "darwin" and machine == "arm64" else "faster-whisper"


def report():
    cmds = INSTALL[os_key()]
    missing = [{"name": t, "install": cmds[t]}
               for t in ("ffmpeg", "uv") if shutil.which(t) is None]
    return {
        "ok": not missing,
        "platform": f"{sys.platform}/{platform.machine()}",
        "whisper_backend": whisper_backend(),
        "whisper_note": ("модель whisper скачается при первом транскрипте "
                         "(~1.5 ГБ, разово); без транскрипта доступен режим "
                         "«только тишина»"),
        "missing": missing,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="только JSON")
    args = ap.parse_args()
    r = report()
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
        return
    print(f"Платформа: {r['platform']}  |  whisper-бэкенд: {r['whisper_backend']}")
    if r["ok"]:
        print("Окружение готово. " + r["whisper_note"])
    else:
        print("Не хватает:")
        for m in r["missing"]:
            print(f"  {m['name']}: {m['install']}")
        print(r["whisper_note"])
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
