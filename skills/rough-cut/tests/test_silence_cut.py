import cutlist
import silence_cut


def test_build_silence_cutlist_finds_gap(media_dir):
    # звук с паузой 1–4с, видео как контейнер (fps/dims/длительность)
    d = silence_cut.build_silence_cutlist(
        media_dir / "clip.mp4", audio=media_dir / "tone_gap.wav", offset=0.0)
    cuts = [s for s in d["segments"] if s["action"] == "cut"]
    assert len(cuts) == 1
    assert cuts[0]["source"] == "silence"
    assert abs(cuts[0]["start"] - 1.15) < 0.3
    cutlist.validate(d)  # тайлинг корректен


def test_single_file_continuous_tone_has_no_cuts(media_dir):
    # у clip.mp4 непрерывный тон → тишины нет → один keep на всё
    d = silence_cut.build_silence_cutlist(media_dir / "clip.mp4")
    assert all(s["action"] == "keep" for s in d["segments"])
    assert d["scenario"] == "screencast"


def test_offset_shifts_cut_into_video_coords(media_dir):
    d = silence_cut.build_silence_cutlist(
        media_dir / "clip.mp4", audio=media_dir / "tone_gap.wav", offset=1.0)
    cut = [s for s in d["segments"] if s["action"] == "cut"][0]
    # пауза 1.15–3.85 в звуке при offset 1.0 → 0.15–2.85 в видео
    assert abs(cut["start"] - 0.15) < 0.3
