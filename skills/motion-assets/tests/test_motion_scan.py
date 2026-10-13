import json
import struct
import subprocess
import zlib

import pytest

import scan_broll


def test_transitions_single_spike():
    diffs = [0.5] * 20
    diffs[7] = 30.0
    assert scan_broll.transitions(diffs) == [[0.7, 0.8]]


def test_transitions_merges_close_windows():
    # авто-зум записи экрана: движение с короткими паузами — одно окно
    diffs = [0.0] * 30
    for i in (5, 6, 8, 10, 11):
        diffs[i] = 9.0
    assert scan_broll.transitions(diffs) == [[0.5, 1.2]]


def test_transitions_keeps_far_windows_apart():
    diffs = [0.0] * 40
    diffs[5] = diffs[20] = 12.0
    assert scan_broll.transitions(diffs) == [[0.5, 0.6], [2.0, 2.1]]


def test_transitions_threshold_and_params():
    diffs = [4.0, 4.01, 3.9]
    assert scan_broll.transitions(diffs) == [[0.1, 0.2]]          # строго больше порога
    assert scan_broll.transitions(diffs, thr=3.5) == [[0.0, 0.3]]
    assert scan_broll.transitions([0, 9, 0, 0, 0, 9], merge_gap=0.0) == [[0.1, 0.2], [0.5, 0.6]]
    assert scan_broll.transitions([0, 9], fps=2) == [[0.5, 1.0]]


def test_transitions_empty():
    assert scan_broll.transitions([]) == []
    assert scan_broll.transitions([1.0, 2.0]) == []


def test_frame_diffs_and_mad():
    frames = [bytes([10] * 4), bytes([10] * 4), bytes([20, 20, 0, 0])]
    assert scan_broll.frame_diffs(frames) == [0.0, 10.0]


def test_draft_entry_is_valid_after_filling():
    import library
    e = scan_broll.draft_entry("demo", 12.345, [[1.0, 1.5]], "demo/demo.mp4")
    assert e["kind"] == "broll" and e["duration"] == 12.35 and e["events"] == []
    assert library.validate_entry(e) == []


def test_rel_to_library(tmp_path):
    lib = tmp_path / "lib"
    (lib / "a").mkdir(parents=True)
    v = lib / "a" / "x.mp4"
    v.write_bytes(b"")
    assert scan_broll.rel_to_library(v, "a", lib) == "a/x.mp4"
    assert scan_broll.rel_to_library(tmp_path / "y.mp4", "b", lib) == "b/y.mp4"


def _png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def _png_pixels(path):
    """Пиксели RGB из PNG, записанного write_png (один IDAT, фильтр 0 на строку)."""
    data = path.read_bytes()
    w, h = struct.unpack(">II", data[16:24])
    i = data.index(b"IDAT")
    n = struct.unpack(">I", data[i - 4:i])[0]
    raw = zlib.decompress(data[i + 4:i + 4 + n])
    stride = w * 3 + 1
    return w, h, b"".join(raw[y * stride + 1:(y + 1) * stride] for y in range(h))


def test_compose_sheet_and_png(tmp_path):
    cw, ch, gap = 120, 90, 2
    frames = [bytes([i * 40 + 40] * (cw * ch * 3)) for i in range(3)]
    sw, sh, buf = scan_broll.compose_sheet(frames, [0.0, 0.5, 1.0], cw, ch, cols=2, rows=2, gap=gap)
    assert (sw, sh) == (2 * cw + 3 * gap, 2 * ch + 3 * gap)
    p = tmp_path / "s.png"
    scan_broll.write_png(p, sw, sh, buf)
    w, h, px = _png_pixels(p)
    assert (w, h) == (sw, sh) and px == bytes(buf)

    def at(x, y):
        return px[(y * sw + x) * 3]
    # низ второй ячейки — кадр как есть; угол первой — плашка таймкода с белыми пикселями
    assert at(gap + cw + gap + 5, gap + ch - 3) == 80
    label = [at(x, y) for x in range(gap + 4, gap + 60) for y in range(gap + 4, gap + 40)]
    assert 0 in label and 255 in label
    # четвёртой ячейки нет — там фон листа
    assert at(sw - 10, sh - 10) == 32


def test_sheet_name_has_range():
    assert scan_broll.sheet_name("demo", 2, 10.0, 19.5) == "demo_sheet02_0010.0-0019.5.png"


def test_cell_size_follows_orientation():
    assert scan_broll.cell_size(1080, 1920) == (216, 384)
    assert scan_broll.cell_size(1920, 1080) == (384, 216)


@pytest.fixture(scope="module")
def cut_video(tmp_path_factory):
    """4 с: тёмный кадр 2 с → резкая смена на светлый 2 с (переход на 2,0 с)."""
    d = tmp_path_factory.mktemp("broll")
    out = d / "cut.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=0x202020:s=270x480:r=30:d=2",
                    "-f", "lavfi", "-i", "color=c=0xE0E0E0:s=270x480:r=30:d=2",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)],
                   check=True)
    return out


@pytest.mark.integration
def test_scan_on_synthetic_cut(cut_video, tmp_path, capsys):
    trans = scan_broll.scan_transitions(cut_video)
    assert len(trans) == 1
    a, b = trans[0]
    assert 1.8 <= a <= 2.0 and 2.0 <= b <= 2.2

    info = scan_broll.probe(cut_video)
    assert (info["width"], info["height"]) == (270, 480) and abs(info["duration"] - 4.0) < 0.1
    sheets = scan_broll.contact_sheets(cut_video, tmp_path, "cut", info["width"], info["height"])
    assert len(sheets) == 1 and sheets[0].name.startswith("cut_sheet01_0000.0-")
    w, h = _png_size(sheets[0])
    assert (w, h) == (5 * 216 + 6 * 4, 4 * 384 + 5 * 4)

    f = scan_broll.frame_at(cut_video, 3.0, tmp_path / "f.png")
    assert f.exists() and _png_size(f) == (270, 480)

    assert scan_broll.main([str(cut_video), "--out", str(tmp_path / "scan"), "--id", "cut",
                            "--json"]) == 0
    res = json.loads(capsys.readouterr().out)
    assert res["entry"]["transitions"] == trans
    assert res["usable"] and (tmp_path / "scan" / "cut.entry.json").exists()
