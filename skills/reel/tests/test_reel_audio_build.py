import json
import subprocess
import sys
from pathlib import Path

import pytest

import check_frames
import composite
import face_centers
import hf
import matte
import music_bed
import plan_md
import tidy
from layout import Build

SCRIPTS = Path(__file__).parent.parent / "scripts"
RECIPE = {"start": 9.67, "loop": [25.796, 38.63], "quiet_end": [40.0, 47.5], "min_start": 5.0}


@pytest.mark.parametrize("dur", [12.0, 30.0, 33.0, 36.6, 61.3, 125.0])
def test_music_plan_sums_and_ends_in_quiet_zone(dur):
    segs = music_bed.plan(dur, RECIPE)
    assert sum(b - a for a, b in segs) == pytest.approx(dur, abs=0.01)
    end = segs[-1][1]
    assert RECIPE["quiet_end"][0] <= end <= RECIPE["quiet_end"][1] + 1e-6
    assert segs[0][0] >= RECIPE["min_start"]


def test_music_loops_only_for_long():
    assert len(music_bed.plan(30.0, RECIPE)) == 1
    assert len(music_bed.plan(125.0, RECIPE)) > 3


def test_long_plan():
    segs = music_bed.long_plan(3, RECIPE)
    assert len(segs) == 5 and segs[-1][1] == pytest.approx(47.2)


def test_gains_and_true_peak():
    assert composite.gains(-20.0, -18.0) == (6.0, -8.0)
    assert composite.gains(-20.0, None) == (6.0, None)
    assert composite.tp_linear(-1.5) == pytest.approx(0.8414, abs=1e-4)


def test_enable_expr():
    assert composite.enable_expr([[0.0, 4.96], [22.08, 23.7]]) == "between(t,0.0,4.96)+between(t,22.08,23.7)"
    assert composite.enable_expr([]) == "0"


def test_final_cmd_with_music_and_front():
    cmd = composite.final_cmd("main.mp4", "front.webm", "rough.mp4", "music.m4a", "out.mp4", 36.5, 2.0, -6.0)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert cmd[cmd.index("front.webm") - 2] == "libvpx-vp9"  # альфа VP9 — декодер явно
    assert "[2:a]volume=2.0dB[vo]" in fc and "[3:a]volume=-6.0dB[mu]" in fc
    assert "amix=inputs=2:duration=first:normalize=0" in fc and "alimiter=limit=0.8128" in fc  # −1,5 dBTP минус 0,3 запаса
    assert cmd[cmd.index("-t") + 1] == "36.500"


def test_final_cmd_without_music_and_front():
    cmd = composite.final_cmd("rough.mp4", None, "rough.mp4", None, "o.mp4", 10, 1.0, None)
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "amix" not in fc and "[1:a]volume=1.0dB[vo]" in fc and "[0:v]null[bv]" in fc


def test_base_cmd():
    cmd = composite.base_cmd("rough.mp4", "behind.webm", "matte/f_%05d.png", [[0, 1]], "base.mp4")
    assert "enable='between(t,0,1)'" in cmd[cmd.index("-filter_complex") + 1]


def test_parse_loudnorm():
    err = 'blah\n[Parsed_loudnorm_0 @ 0x1]\n{\n\t"input_i" : "-23.54",\n\t"input_tp" : "-4.10",\n' \
          '\t"normalization_type" : "dynamic"\n}\n'
    d = composite.parse_loudnorm(err)
    assert d["input_i"] == -23.54 and d["input_tp"] == -4.1 and "normalization_type" not in d


def test_readme_rows():
    text = composite.readme_rows({"C1 — v4.mp4": {"variant": "v4", "label": "по слову", "duration": 36.6}})
    assert "`C1 — v4.mp4` | 36.6 с. по слову (вариант v4)" in text


def test_matte_frame_ranges_and_gaps():
    assert matte.frame_ranges([[1.0, 2.0]], fps=30) == [(16, 31, 63)]  # t=1.0 — кадр 31
    assert matte.frame_ranges([[0.0, 0.5]], fps=30) == [(1, 1, 18)]
    assert matte.gaps([2, 3], 5) == [1, 4, 5]


def test_face_rows_to_times():
    csv_text = "name,cx,cy\nf_00001.png,0.5,0.4\nf_00011.png,,\n"
    assert face_centers.rows_to_times(csv_text, 10) == [(0.0, 0.5, 0.4), (1.0, None, None)]


def test_check_frames_sample_times():
    brolls = [{"a": 1.0, "b": 2.0, "n": 0, "layout": "half"}]
    cards = [{"a": 3.0, "b": 5.0, "template": "cta"}]
    times = check_frames.sample_times(brolls, cards, [[0.0, 2.0], [6.0, 7.0]], 10.0)
    labels = [lbl for _, lbl in times]
    assert labels.count("маска") == 30
    assert "б-ролл #1 half" in labels and "карточка cta" in labels
    assert (1.5, "б-ролл #1 half") in times and times == sorted(times)


def test_plan_md_gaps():
    assert plan_md.gaps([(1.0, 2.0), (1.5, 3.0), (5.0, 6.0)], 8.0) == [(0.0, 1.0), (3.0, 5.0), (6.0, 8.0)]
    assert plan_md.gaps([(0.0, 7.9)], 8.0) == []


def test_tidy_plan(tmp_path):
    ex = tmp_path / "export"
    (ex / "final").mkdir(parents=True)
    (ex / "final" / "x — v4.mp4").write_bytes(b"1")
    (ex / "final" / "notes.txt").write_text("x")
    (ex / "C1.cutlist.json").write_text("{}")
    b = ex / "_сборка"
    for v in ("v2", "v4"):
        (b / v / "main").mkdir(parents=True)
        (b / v / "plan.json").write_text("{}")
        (b / v / "main" / "index.html").write_text("")
        (b / v / "main" / "broll.mp4").write_bytes(b"123")
    (b / "v4" / "matte").mkdir()
    acts = {(a, p.relative_to(ex).as_posix()) for a, p, _, _ in tidy.plan_tidy(ex, keep=["v4"])}
    assert ("move", "C1.cutlist.json") in acts and ("move", "final/notes.txt") in acts
    assert ("delete", "_сборка/v2") in acts
    assert ("delete", "_сборка/v4/matte") in acts and ("delete", "_сборка/v4/main/broll.mp4") in acts
    assert not any(p.endswith("index.html") or p.endswith("plan.json") for _, p in acts)
    assert not any(p == "final/x — v4.mp4" for _, p in acts)


def test_tidy_dry_run_changes_nothing(tmp_path):
    ex = tmp_path / "export"
    ex.mkdir()
    (ex / "stray.mp4").write_bytes(b"1")
    subprocess.run([sys.executable, str(SCRIPTS / "tidy.py"), str(ex)], check=True, capture_output=True)
    assert (ex / "stray.mp4").exists()


def test_layout_picks_rough_cut_names(tmp_path):
    root = tmp_path / "export" / "_сборка"
    (root / "v1").mkdir(parents=True)
    (root / "C9.cutlist.json").write_text(json.dumps({"inputs": {"video": "/src/C9.MP4"}}))
    (root / "C9.cutlist.pregaze.json").write_text("{}")
    (root / "C9.roughcut.mp4").write_bytes(b"")
    b = Build(root / "v1")
    assert b.cutlist.name == "C9.cutlist.json" and b.roughcut.name == "C9.roughcut.mp4"
    assert b.stem == "C9" and b.final == tmp_path / "export" / "final"


def test_hf_page_and_render_cmd():
    html = hf.page(".x{}", "<div></div>", "tl.set();", 12.3456, fonts={"main": "main.ttf", "display": None})
    assert 'data-duration="12.346"' in html and 'url("assets/main.ttf")' in html and '"ReelDisplay"; src' not in html
    cmd = hf.render_cmd("proj", "out.webm", "webm")
    assert f"hyperframes@{hf.HF_VERSION}" in cmd and cmd[cmd.index("--format") + 1] == "webm"


def test_hf_setup_project_copies_theme_fonts(tmp_path, monkeypatch):
    g = tmp_path / "gsap.js"
    g.write_text("//gsap")
    monkeypatch.setattr(hf, "ensure_gsap", lambda: g)
    font = tmp_path / "Font.TTF"
    font.write_bytes(b"f")
    fonts = hf.setup_project(tmp_path / "proj", {"font_main": font, "font_display": None})
    assert fonts == {"main": "main.ttf", "display": None}
    assert (tmp_path / "proj" / "assets" / "main.ttf").exists()
    assert (tmp_path / "proj" / "assets" / "gsap.min.js").read_text() == "//gsap"


@pytest.mark.integration
def test_build_front_and_plan_md_end_to_end(tmp_path, clip_mp4, settings_file, monkeypatch):
    """Сквозная сборка без рендера: черновик 3 с, расшифровка, план → front/index.html и PLAN.md."""
    root = tmp_path / "export" / "_сборка"
    v = root / "v1"
    v.mkdir(parents=True)
    (root / "roughcut.mp4").symlink_to(clip_mp4)
    ws = [{"text": t, "start": 0.2 + i * 0.5, "end": 0.6 + i * 0.5} for i, t in enumerate("Сервер работает сам. Напиши СЛОВО".split())]
    (root / "transcript.json").write_text(json.dumps({"text": "", "words": ws}, ensure_ascii=False))
    plan = {"version": 1, "mode": "full", "accent_words": ["сам"], "punch_words": ["сам"],
            "items": [{"kind": "card", "template": "cta", "from": "Напиши", "to": "end",
                       "slots": {"lead": "Напиши в комменты", "word": "СЛОВО"}},
                      {"kind": "missing", "at": "Сервер", "want": "серверная стойка"}]}
    plan["items"][0]["to"] = 2.98
    (v / "plan.json").write_text(json.dumps(plan, ensure_ascii=False))
    g = tmp_path / "gsap.js"
    g.write_text("//")
    env = {"HOME": str(tmp_path)}
    (tmp_path / ".cache" / "reel").mkdir(parents=True)
    (tmp_path / ".cache" / "reel" / f"gsap-{hf.GSAP_VERSION}.min.js").write_text("//")
    import os
    run_env = dict(os.environ, **env)
    for script in ("plan_md.py", "build_front.py"):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), str(v), "--settings", str(settings_file)],
                           capture_output=True, text=True, env=run_env)
        assert r.returncode == 0, r.stderr
    md = (v / "PLAN.md").read_text()
    assert "| время | слово | что появляется | раскладка | наезд |" in md
    assert "серверная стойка → карточка или motion-assets" in md
    html = (v / "front" / "index.html").read_text()
    assert 'id="c1"' in html and "СЛОВО" in html and (v / "front" / "assets" / "main.ttf").exists()
