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


def _export_with_build(tmp_path):
    """export/ с роликом, мусором, старой final/ и двумя вариантами; исходники — рядом."""
    src = tmp_path / "C1.MP4"
    src.write_bytes(b"video")
    (tmp_path / "C1.mov").write_bytes(b"sound")
    ex = tmp_path / "export"
    (ex / "final").mkdir(parents=True)
    (ex / "x — v4.mp4").write_bytes(b"1")
    (ex / "final" / "old — v2.mp4").write_bytes(b"1")
    (ex / "final" / "README.md").write_text("x")
    (ex / "notes.txt").write_text("x")
    b = ex / "_сборка"
    b.mkdir()
    (b / "C1.cutlist.json").write_text(json.dumps({"inputs": {"video": str(src), "audio": "C1.mov"}}))
    for v in ("v2", "v4"):
        (b / v / "main").mkdir(parents=True)
        (b / v / "plan.json").write_text("{}")
        (b / v / "main" / "index.html").write_text("")
        (b / v / "main" / "broll.mp4").write_bytes(b"123")
    (b / "v4" / "matte").mkdir()
    return ex


def test_tidy_plan(tmp_path):
    ex = _export_with_build(tmp_path)
    acts = {(a, p.relative_to(ex).as_posix()) for a, p, _, _ in tidy.plan_tidy(ex, keep=["v4"])}
    assert ("move", "notes.txt") in acts and ("move", "final/README.md") in acts
    assert ("move", "final/old — v2.mp4") in acts  # старая раскладка: ролик поднимается в export/
    assert ("delete", "_сборка/v2") in acts
    assert ("delete", "_сборка/v4/matte") in acts and ("delete", "_сборка/v4/main/broll.mp4") in acts
    assert not any(p.endswith("index.html") or p.endswith("plan.json") for _, p in acts)
    assert not any(p == "x — v4.mp4" for _, p in acts)


def test_tidy_done_keeps_only_reels_and_asks_about_sources(tmp_path):
    ex = _export_with_build(tmp_path)
    assert tidy.sources(ex) == [(tmp_path / "C1.MP4").resolve(), (tmp_path / "C1.mov").resolve()]
    acts = {(a, p.name) for a, p, _, _ in tidy.plan_done(ex)}
    assert ("delete", "_сборка") in acts and ("delete", "notes.txt") in acts
    assert ("move", "old — v2.mp4") in acts and ("delete", "README.md") in acts
    assert not any(n in ("C1.MP4", "C1.mov", "x — v4.mp4") for _, n in acts)  # исходники — только по «да»
    subprocess.run([sys.executable, str(SCRIPTS / "tidy.py"), str(ex), "--done", "--apply"], check=True, capture_output=True)
    assert sorted(p.name for p in ex.iterdir()) == ["old — v2.mp4", "x — v4.mp4"]
    assert (tmp_path / "C1.MP4").exists() and (tmp_path / "C1.mov").exists()


def test_tidy_done_sources_after_yes(tmp_path):
    ex = _export_with_build(tmp_path)
    subprocess.run([sys.executable, str(SCRIPTS / "tidy.py"), str(ex), "--done", "--sources", "--apply"],
                   check=True, capture_output=True)
    assert not (tmp_path / "C1.MP4").exists() and not (tmp_path / "C1.mov").exists()
    assert (ex / "x — v4.mp4").exists()
    r = subprocess.run([sys.executable, str(SCRIPTS / "tidy.py"), str(ex), "--sources"], capture_output=True)
    assert r.returncode != 0  # без --done исходники не трогаются


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
    assert b.stem == "C9" and b.final == tmp_path / "export"


def test_hf_page_and_render_cmd():
    html = hf.page(".x{}", "<div></div>", "tl.set();", 12.3456, fonts={"main": "main.ttf", "display": None})
    assert 'data-duration="12.346"' in html and 'url("assets/main.ttf")' in html and '"ReelDisplay"; src' not in html
    cmd = hf.render_cmd("proj", "out.webm", "webm")
    assert f"hyperframes@{hf.HF_VERSION}" in cmd and cmd[cmd.index("--format") + 1] == "webm"
    assert "--video-frame-format" not in cmd
    hi = hf.render_cmd("proj", "out.mp4", "mp4", "high")   # high: кадры исходного видео без JPEG
    assert hi[hi.index("--quality") + 1] == "high" and hi[hi.index("--video-frame-format") + 1] == "png"


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


def test_music_level_envelope_expr():
    e = composite.level_expr([(0.0, -10.0, 0.01), (24.3, 8.0, 0.3), (26.0, 0.0, 0.8)])
    assert e.startswith("if(lt(t,0.000),0.0") and e.rstrip(")").endswith(",0.0")
    assert "if(lt(t,24.300),-10.0" in e and "(t-26.000)/0.800" in e
    cmd = composite.final_cmd("v.mp4", None, "voice.mp4", "m.m4a", "out.mp4", 30.0, 1.0, -3.0,
                         levels=[(1.0, 6.0, 0.5)])
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "volume=-3.0dB,volume='pow(10,(" in fc and "eval=frame" in fc


def test_matte_frames_on_reel_fps_grid():
    """Черновик с камеры 50 к/с: кадры маски обязаны браться на сетке 30 к/с, иначе человек отстаёт."""
    import matte
    cmd = matte.extract_cmd("rc.mp4", 871, 1001, "out/f_%05d.png")
    assert cmd[cmd.index("-vf") + 1] == "fps=30"
    assert cmd[cmd.index("-ss") + 1] == f"{870 / 30:.4f}" and cmd.index("-ss") > cmd.index("-i")


def test_final_mixes_sfx_track():
    cmd = composite.final_cmd("v.mp4", "f.webm", "voice.mp4", "m.m4a", "o.mp4", 30.0, 1.0, -3.0, sfx="sfx.wav")
    fc = cmd[cmd.index("-filter_complex") + 1]
    assert "sfx.wav" in cmd and "[vo][mu][sx]amix=inputs=3" in fc
    cmd = composite.final_cmd("v.mp4", None, "voice.mp4", None, "o.mp4", 30.0, 1.0, None, sfx="sfx.wav")
    assert "[vo][sx]amix=inputs=2" in cmd[cmd.index("-filter_complex") + 1]


def test_sfx_synth_catalog_and_bed():
    import importlib.util
    if importlib.util.find_spec("numpy") is None:
        pytest.skip("numpy только в uv-окружении sfx.py")
    import sfx
    for name in sfx.SOUNDS:
        y = sfx.synth(name)
        assert y.ndim == 2 and y.shape[1] == 2 and 0.03 < len(y) / sfx.SR < 1.5 and abs(y).max() <= 1.0001
    bed = sfx.place([(0.5, "whoosh", -10, None), (1.0, "type", -12, 0.6)], 3.0)
    assert bed.shape == (3 * sfx.SR, 2) and abs(bed).max() < 0.5


def test_sfx_variants_rotate_in_time_order(tmp_path, monkeypatch):
    import importlib.util
    if importlib.util.find_spec("numpy") is None:
        pytest.skip("numpy только в uv-окружении sfx.py")
    import sfx
    for stem in ("pop", "pop-2", "pop-3", "tap"):
        sfx.write_wav(tmp_path / f"{stem}.wav", sfx.synth("tap"))
    assert [p.stem for p in sfx.variants("pop", tmp_path)] == ["pop", "pop-2", "pop-3"]
    assert [p.stem for p in sfx.variants("tap", tmp_path)] == ["tap"] and sfx.variants("swish", tmp_path) == []
    used = []
    monkeypatch.setattr(sfx, "read_wav", lambda p: (used.append(Path(p).stem), sfx.synth("tap"))[1])
    sfx.place([(2.0, "pop", -12, None), (0.5, "pop", -12, None), (1.0, "pop", -12, None), (1.5, "pop", -12, None)], 3.0, tmp_path)
    assert used == ["pop", "pop-2", "pop-3", "pop"]               # по времени, по кругу


def test_film_roll_copies_and_accelerating_passes():
    import build_main
    durs = build_main.roll_durations(0.8, 4)
    assert abs(sum(durs) - 0.8) < 1e-3 and all(a > b for a, b in zip(durs, durs[1:]))
    html = build_main.render_html(10.0, [], [], [], "#000000", [], rolls=[(1.0, 0.8, 4)])
    assert 'id="fu0"' in html and 'id="fd0"' in html and 'data-media-start="1.000"' in html
    assert html.count('tl.fromTo("#reel"') == 4 and 'tl.set("#reel", {y: 0}' in html


# ── музыка громче в паузах, на месте под голосом ─────────────────────────────

def _w(*spans):
    return [{"text": f"w{i}", "start": a, "end": b} for i, (a, b) in enumerate(spans)]


def test_auto_levels_lift_in_pauses_flat_under_speech():
    words = _w((0.5, 1.0), (1.2, 2.0), (3.5, 4.2), (4.5, 5.0))   # пауза 2.0–3.5, 4.2–4.5 короткая
    keys = composite.auto_levels(words, 7.0, lift_db=6)
    lv = lambda t: composite.level_at(keys, t)  # noqa: E731
    assert lv(0.05) == 6 and lv(1.5) == 0 and lv(4.3) == 0      # до речи громче; под голосом и в короткой паузе — нет
    assert lv(2.9) == 6 and lv(3.5) == 0                          # длинная пауза поднялась и к фразе опустилась
    assert lv(6.8) == 6                                           # после последнего слова — громче
    assert [k[0] for k in keys] == sorted(k[0] for k in keys)


def test_auto_levels_off_and_tight_speech():
    assert composite.auto_levels(_w((0.0, 1.0)), 5.0, lift_db=0) == []
    keys = composite.auto_levels(_w((0.0, 1.0), (1.3, 2.0), (2.4, 3.0)), 3.05, lift_db=6)
    assert keys == []                                             # речь сплошная, концы впритык


def test_level_at_matches_ramp():
    keys = [(1.0, -6.0, 1.0)]
    assert composite.level_at(keys, 0.5) == 0 and composite.level_at(keys, 1.5) == -3.0
    assert composite.level_at(keys, 3.0) == -6.0


def test_sfx_takes_own_wav_by_path(tmp_path):
    np = pytest.importorskip("numpy")
    import sfx
    y = (np.sin(np.linspace(0, 200, sfx.SR // 2)) * 0.5).astype(np.float32)
    p = tmp_path / "sting.wav"
    sfx.write_wav(p, np.stack([y, y], axis=1))
    bed = sfx.place([(0.5, str(p), -10, None)], 2.0)
    assert abs(bed[: sfx.SR // 4]).max() == 0          # до звука тишина
    assert abs(bed[sfx.SR // 2: sfx.SR]).max() > 0.2   # свой файл на месте


def test_tidy_done_keeps_publication_texts_next_to_reels(tmp_path):
    ex = tmp_path / "export"
    (ex / "_сборка").mkdir(parents=True)
    (ex / "R — YouTube.mp4").write_bytes(b"x")
    (ex / "R — YouTube.txt").write_text("тайтл")
    (ex / "заметка.txt").write_text("мусор")
    acts = {p.name for a, p, _, _ in tidy.plan_done(ex) if a == "delete"}
    assert "R — YouTube.txt" not in acts
    assert "заметка.txt" in acts and "_сборка" in acts
