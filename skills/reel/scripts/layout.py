"""Раскладка папки сборки. Только stdlib.

export/                      ← рядом с исходниками (как у rough-cut)
  <стем> — <метка>.mp4       ← готовый ролик, прямо здесь
  _сборка/                   ← живёт, пока идёт работа; финал принят — удаляется (tidy.py --done)
    <стем>.cutlist.json      ← cut-list rough-cut (канон резки; имя — как у rough-cut)
    <стем>.roughcut.mp4      ← смонтированный черновик; в режиме subs — ссылка
                               roughcut.mp4 на чужой смонтированный файл
    words.raw.json           ← пословная расшифровка Whisper
    transcript.json          ← после словаря замен и подгонки к звуку
    faces.csv                ← центр лица по времени (для наездов)
    music.m4a                ← подложка под длину ролика
    v1/                      ← вариант: план и слои
      plan.json, PLAN.md
      windows.json           ← окна «текст за головой» (маска)
      half_windows.json      ← окна half (субтитры на стык)
      behind/  main/  front/ ← проекты HyperFrames
      base.mp4 main.mp4 front.webm behind.webm
      matte/                 ← кадры маски (удаляются после вшивания)

Каждый скрипт принимает папку варианта и находит общие файлы уровнем выше.
"""
import json
from pathlib import Path


def _pick(root, pattern, default):
    found = sorted(root.glob(pattern))
    return found[0] if found else root / default


class Build:
    def __init__(self, variant_dir):
        self.var = Path(variant_dir).resolve()
        self.root = self.var.parent
        self.export = self.root.parent
        self.final = self.export          # готовые ролики — прямо в export/
        r, v = self.root, self.var
        self.cutlist = _pick(r, "*.cutlist.json", "cutlist.json")
        self.roughcut = _pick(r, "*.roughcut.mp4", "roughcut.mp4")
        self.words_raw = r / "words.raw.json"
        self.transcript = r / "transcript.json"
        self.faces = r / "faces.csv"
        self.music = r / "music.m4a"
        self.plan = v / "plan.json"
        self.plan_md = v / "PLAN.md"
        self.windows = v / "windows.json"
        self.half_windows = v / "half_windows.json"
        self.behind = v / "behind"
        self.main = v / "main"
        self.front = v / "front"
        self.base = v / "base.mp4"
        self.main_mp4 = v / "main.mp4"
        self.front_webm = v / "front.webm"
        self.behind_webm = v / "behind.webm"
        self.matte = v / "matte"

    @property
    def name(self):
        return self.var.name

    @property
    def stem(self):
        """Имя исходника: из cut-list, иначе из того, на что указывает roughcut.mp4."""
        if self.cutlist.exists():
            v = json.loads(self.cutlist.read_text(encoding="utf-8"))["inputs"]["video"]
            return Path(v).stem
        if self.roughcut.is_symlink():
            return Path(self.roughcut.resolve()).stem
        return self.export.parent.name

    def load_plan(self):
        return json.loads(self.plan.read_text(encoding="utf-8"))

    def read_json(self, path, default=None):
        p = Path(path)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def write_json(self, path, data):
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
