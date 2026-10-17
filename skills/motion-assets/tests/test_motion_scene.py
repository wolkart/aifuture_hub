import json

import pytest

import library
import scene


def test_list_templates():
    assert scene.list_templates() == ["big_word", "brand_reveal", "channel_feed", "chat_3d", "coin_flip", "end_card", "flip_board", "laptop_3d", "logo_row", "music_eq", "post_3d", "sources_bot", "timeline_3d"]


def test_cli_list(capsys):
    assert scene.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "coin_flip" in out and "headline" in out
    assert scene.main(["list", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {d["name"] for d in data} == set(scene.list_templates())


def test_write_project(tmp_path, theme, fake_gsap):
    tpl = scene.load_template("coin_flip")
    built = scene.write_project(tpl, {}, theme, tmp_path / "p")
    html = (tmp_path / "p" / "index.html").read_text(encoding="utf-8")
    assert (tmp_path / "p" / "assets" / "gsap.min.js").exists()
    assert 'data-composition-id="main"' in html and f'data-duration="{built["duration"]:.3f}"' in html
    assert "window.__timelines" in html and 'id="coin"' in html


def test_scene_cli_without_render(tmp_path, fake_gsap, capsys):
    slots = tmp_path / "slots.json"
    (tmp_path / "icons").mkdir()
    (tmp_path / "icons" / "i.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    slots.write_text(json.dumps({"headline": "Мой *бот*", "icon": "icons/i.png"},
                                ensure_ascii=False), encoding="utf-8")
    lib = tmp_path / "lib"
    rc = scene.main(["coin_flip", "--id", "my-coin", "--slots", str(slots), "--library", str(lib),
                     "--tags", "бот, тест", "--settings", str(tmp_path / "нет.json")])
    assert rc == 0
    proj = lib / "my-coin"
    assert (proj / "index.html").exists() and (proj / "icon.png").exists()
    e = library.get(library.load(lib), "my-coin")
    assert e["kind"] == "scene" and e["layout"] == "full" and e["theme"] == "dark"
    assert e["files"] == {"project": "my-coin/index.html"}
    assert "бот" in e["tags"] and "тест" in e["tags"] and "иконка" in e["tags"]
    assert e["slots"]["headline"] == "Мой *бот*" and e["template"] == "coin_flip"
    assert library.validate(library.load(lib)) == []
    assert "нейтральная тема" in capsys.readouterr().out


def test_scene_overlay_entry_kind(tmp_path, fake_gsap):
    lib = tmp_path / "lib"
    scene.main(["sources_bot", "--id", "ov", "--layout", "overlay", "--library", str(lib),
                "--settings", str(tmp_path / "нет.json")])
    e = library.get(library.load(lib), "ov")
    assert e["kind"] == "overlay" and e["layout"] == "overlay" and e["theme"] == "light"
    html = (lib / "ov" / "index.html").read_text(encoding="utf-8")
    assert "background: transparent" in html


def test_scene_rerun_replaces_entry(tmp_path, fake_gsap):
    lib = tmp_path / "lib"
    args = ["flip_board", "--id", "b", "--library", str(lib), "--settings", str(tmp_path / "x.json")]
    scene.main(args)
    scene.main(args + ["--theme", "dark", "--layout", "half"])
    idx = library.load(lib)
    assert len(idx["assets"]) == 1 and idx["assets"][0]["layout"] == "half"


def test_scene_errors(tmp_path, fake_gsap):
    with pytest.raises(SystemExit):
        scene.main(["nope", "--id", "x", "--library", str(tmp_path)])
    with pytest.raises(SystemExit):
        scene.main(["coin_flip", "--library", str(tmp_path)])
    bad = tmp_path / "s.json"
    bad.write_text('{"headlin": "x"}', encoding="utf-8")
    with pytest.raises(ValueError):
        scene.main(["coin_flip", "--id", "x", "--slots", str(bad), "--library", str(tmp_path),
                    "--settings", str(tmp_path / "x.json")])


def test_render_helpers():
    assert scene.has_alpha("yuva444p12le") and scene.has_alpha("rgba")
    assert not scene.has_alpha("yuv420p")
    g = scene.green_cmd("a.mov", "g.mp4", 1080, 1920)
    assert "color=c=0x00FF00:s=1080x1920:r=30" in g and "[0:v][1:v]overlay=shortest=1,format=yuv420p" in g
    p = scene.prores_cmd("a.webm", "a.mov", "libvpx-vp9")
    assert p[:6] == ["ffmpeg", "-y", "-v", "error", "-c:v", "libvpx-vp9"]
    assert "prores_ks" in p and "yuva444p10le" in p
    pv = scene.preview_cmd("a.mp4", 1.5, "p.png")
    assert pv.index("-i") < pv.index("-ss")                      # точный кадр: -ss после -i


def test_entry_for_paths_relative():
    built = {"layout": "overlay", "duration": 3.0, "theme_kind": "dark", "tags": ["x"],
             "describes": "d", "events": [{"t": 0.1, "what": "a"}]}
    e = scene.entry_for("id1", "coin_flip", built, {}, {"mov_alpha": "id1.mov", "green": "id1-green.mp4"})
    assert e["files"] == {"mov_alpha": "id1/id1.mov", "green": "id1/id1-green.mp4"}
    assert e["kind"] == "overlay"
    assert library.validate_entry(e) == []


def test_scripts_and_templates_compile_with_system_python():
    """scene.py запускают системным python3 (на маке 3.9): синтаксис новее него ронял рендер."""
    import shutil
    import subprocess
    from pathlib import Path
    py = shutil.which("python3")
    if not py:
        return
    root = Path(__file__).parent.parent
    for f in sorted(list((root / "scripts").glob("*.py")) + list((root / "templates").glob("*.py"))):
        r = subprocess.run([py, "-m", "py_compile", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f.name}: {r.stderr.strip()[-300:]}"
