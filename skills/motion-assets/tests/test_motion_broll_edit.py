import subprocess

import pytest

import broll_edit as be

LAND = {"width": 1920, "height": 1080, "duration": 10.0}
PORT = {"width": 1080, "height": 1920, "duration": 10.0}


def test_crop_rect_landscape_focus():
    assert be.crop_rect(1920, 1080) == (608, 1080, 656, 0)
    assert be.crop_rect(1920, 1080, focus_x=0.0) == (608, 1080, 0, 0)      # прижат к краю
    assert be.crop_rect(1920, 1080, focus_x=1.0) == (608, 1080, 1312, 0)
    assert be.crop_rect(1920, 1080, focus_x=0.25) == (608, 1080, 176, 0)


def test_crop_rect_portrait_and_taller():
    assert be.crop_rect(1080, 1920) == (1080, 1920, 0, 0)                  # уже 9:16
    w, h, x, y = be.crop_rect(1170, 2532)                                  # айфон: выше 9:16
    assert (w, x) == (1170, 0) and h == 2080 and y == 226
    assert w % 2 == 0 and h % 2 == 0


def test_crop_chain():
    assert be.crop_chain((608, 1080, 656, 0)) == \
        "crop=608:1080:656:0,scale=1080:1920:flags=lanczos,setsar=1"


def test_zoom_chain_uses_scale_eval_frame_not_zoompan():
    s = be.zoom_chain(1.0, 3.0, 0.3, 0.6, 1.5, ramp=0.4)
    assert "zoompan" not in s
    assert "eval=frame" in s and "crop=1080:1920:'(iw-1080)*0.3000':'(ih-1920)*0.6000'" in s
    assert "(t-1.000)/0.400" in s and "(t-2.600)/0.400" in s                # вход и выход
    assert "1+0.5000*" in s


def test_zoom_ramp_capped_by_segment():
    s = be.zoom_chain(1.0, 1.4, 0.5, 0.5, 1.2, ramp=1.0)
    assert "/0.200" in s


def test_ease_expr_is_smoothstep():
    e = be.ease_expr(0, 2, 0.5)
    assert e.count("(3-2*") == 2


def test_blur_graph_two_boxes():
    g = be.blur_graph([{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05, "from": 1, "to": 2.5},
                       {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.1, "from": 4, "to": 5}], 1000, 2000)
    assert g.startswith("[0:v]split=3[bb0][bs0][bs1]")
    assert "[bs0]crop=300:100:100:400,boxblur=lr=30:lp=3:cr=15:cp=3[bl0]" in g
    assert "[bb0][bl0]overlay=100:400:enable='between(t,1.000,2.500)'[bb1]" in g
    assert "[bb1][bl1]overlay=500:1000:enable='between(t,4.000,5.000)'[vb]" in g


def test_blur_radius_fits_small_box():
    g = be.blur_graph([{"x": 0, "y": 0, "w": 0.2, "h": 0.2, "from": 0, "to": 1}], 640, 360)
    assert "crop=128:72:0:0,boxblur=lr=30:lp=3:cr=15:cp=3" in g      # 72 → лума < 36, хрома < 18
    g = be.blur_graph([{"x": 0, "y": 0, "w": 0.01, "h": 0.01, "from": 0, "to": 1}], 640, 360)
    assert "boxblur=lr=1:lp=3:cr=0:cp=3" in g                         # крошечный бокс


def test_speed_pieces_cover_whole_duration():
    p = be.speed_pieces([[6, 8, 4], [2, 3, 2]], 10.0)
    assert p == [(0.0, 2, 1.0), (2, 3, 2.0), (3, 6, 1.0), (6, 8, 4.0), (8, 10.0, 1.0)]
    assert be.speed_pieces([[0, 10, 3]], 10.0) == [(0, 10, 3.0)]
    assert be.speed_pieces([[8, 20, 2]], 10.0) == [(0.0, 8, 1.0), (8, 10.0, 2.0)]


def test_speed_graph():
    g = be.speed_graph([[2, 4, 3]], 6.0, "vc", "vout")
    assert g.startswith("[vc]split=3[sp0][sp1][sp2]")
    assert "[sp1]trim=start=2.000:end=4.000,setpts=(PTS-STARTPTS)/3[sq1]" in g
    assert "[sp0]trim=start=0.000:end=2.000,setpts=PTS-STARTPTS[sq0]" in g
    assert g.endswith("[sq0][sq1][sq2]concat=n=3:v=1:a=0,fps=30[vout]")


def test_map_point_into_crop():
    rect = be.crop_rect(1920, 1080)                       # x 656…1264
    assert be.map_point(0.5, 0.5, rect, 1920, 1080) == (0.5, 0.5)
    assert be.map_point(0.0, 0.5, rect, 1920, 1080) == (0.0, 0.5)    # вне кадрирования → край


def test_filter_complex_order():
    fc = be.filter_complex(LAND, zooms=[{"t0": 1, "t1": 3, "cx": 0.5, "cy": 0.5, "scale": 1.3}],
                           blurs=[{"x": 0, "y": 0, "w": 0.1, "h": 0.1, "from": 0, "to": 1}],
                           speeds=[[5, 7, 2]])
    i_blur, i_crop, i_zoom, i_speed = (fc.index("boxblur"), fc.index("crop=608"),
                                       fc.index("eval=frame"), fc.index("concat"))
    assert i_blur < i_crop < i_zoom < i_speed
    assert fc.endswith("[vout]")


def test_filter_complex_plain_crop():
    assert be.filter_complex(PORT) == \
        "[0:v]crop=1080:1920:0:0,scale=1080:1920:flags=lanczos,setsar=1,fps=30[vout]"


def test_build_cmd_never_overwrites_source(tmp_path):
    v = tmp_path / "a.mp4"
    with pytest.raises(ValueError):
        be.build_cmd(v, v, "[0:v]null[vout]")
    cmd = be.build_cmd(v, tmp_path / "b.mp4", "[0:v]null[vout]")
    assert cmd[-1].endswith("b.mp4") and "-an" in cmd


def test_cli_parsers():
    assert be.parse_zoom("1,3,0.4,0.5,1.5") == {"t0": 1, "t1": 3, "cx": 0.4, "cy": 0.5, "scale": 1.5}
    assert be.parse_zoom("1,3,0.4,0.5,1.5,0.2")["ramp"] == 0.2
    assert be.parse_blur("0.1,0.2,0.3,0.4,1,2")["to"] == 2
    assert be.parse_speed("2,4,3") == [2, 4, 3]


@pytest.mark.integration
def test_edit_synthetic(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                    "testsrc2=duration=4:size=640x360:rate=30", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(src)], check=True)
    out = tmp_path / "lib" / "demo" / "demo.mp4"
    assert be.main([str(src), "--out", str(out), "--zoom", "0.5,2.5,0.5,0.5,1.4",
                    "--blur", "0.1,0.1,0.2,0.2,0,1", "--speed", "3,4,2"]) == 0
    import scan_broll
    info = scan_broll.probe(out)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert abs(info["duration"] - 3.5) < 0.1
    assert src.stat().st_size > 0
    with pytest.raises(SystemExit):
        be.main([str(src), "--out", str(out)])            # без --force не перезаписывает
