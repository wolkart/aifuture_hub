import json

import pytest

import library


def scene(id_="tg-coin", **kw):
    e = {"id": id_, "kind": "scene", "layout": "full", "duration": 3.3, "theme": "dark",
         "tags": ["telegram", "канал"], "describes": "Глянцевый значок переворачивается, круги",
         "events": [{"t": 0.15, "what": "значок появляется"}, {"t": 1.75, "what": "переворот"}],
         "slots": {"headline": "текст"}, "files": {"mp4": f"{id_}/{id_}.mp4"}}
    e.update(kw)
    return e


def broll(**kw):
    e = {"id": "term-deploy", "kind": "broll", "layout": "full", "duration": 10.0, "theme": "dark",
         "tags": ["терминал"], "describes": "деплой в терминале",
         "events": [{"t": 1.0, "what": "команда видна целиком"}, {"t": 4.5, "what": "клик «Ёлка»"}],
         "transitions": [[2.0, 2.4], [6.0, 6.3]],
         "private": [{"from": 7.0, "to": 8.0, "what": "IP в заголовке"}],
         "files": {"mp4": "term-deploy/term-deploy.mp4"}}
    e.update(kw)
    return e


# ── валидация ────────────────────────────────────────────────────────────────

def test_valid_entries_pass():
    assert library.validate_entry(scene()) == []
    assert library.validate_entry(broll()) == []


@pytest.mark.parametrize("patch, needle", [
    ({"kind": "video"}, "kind"),
    ({"layout": "side"}, "layout"),
    ({"theme": "grey"}, "theme"),
    ({"duration": 0}, "duration"),
    ({"id": "с пробелом"}, "id"),
    ({"kind": "overlay", "layout": "full"}, "overlay"),
    ({"events": [{"t": 2.0, "what": "a"}, {"t": 1.0, "what": "b"}]}, "порядок"),
    ({"events": [{"t": 9.0, "what": "a"}]}, "вне"),
    ({"events": [{"t": 1.0}]}, "events"),
    ({"files": {"mp4": "/abs/path.mp4"}}, "относительно"),
    ({"files": {"mp4": "../x.mp4"}}, "относительно"),
    ({"tags": "один"}, "tags"),
])
def test_invalid_scene(patch, needle):
    errs = library.validate_entry(scene(**patch))
    assert errs and any(needle in e for e in errs), errs


@pytest.mark.parametrize("patch, needle", [
    ({"transitions": [[3.0, 2.0]]}, "transitions"),
    ({"transitions": [[1.0, 11.0]]}, "transitions"),
    ({"transitions": [1.0, 2.0]}, "transitions"),
    ({"private": [{"from": 8.0, "to": 7.0, "what": "x"}]}, "private"),
    ({"private": [{"from": 1.0}]}, "private"),
])
def test_invalid_broll(patch, needle):
    errs = library.validate_entry(broll(**patch))
    assert errs and any(needle in e for e in errs), errs


def test_validate_index_duplicate_ids():
    idx = {"version": 1, "assets": [scene(), scene()]}
    assert any("повторяется" in e for e in library.validate(idx))


def test_add_or_replace():
    idx = library.empty()
    library.add_or_replace(idx, scene())
    library.add_or_replace(idx, broll())
    library.add_or_replace(idx, scene(duration=4.0))
    assert [e["id"] for e in idx["assets"]] == ["tg-coin", "term-deploy"]
    assert idx["assets"][0]["duration"] == 4.0
    with pytest.raises(ValueError):
        library.add_or_replace(idx, scene(kind="nope"))


def test_save_load_roundtrip(tmp_path):
    assert library.load(tmp_path) == library.empty()
    library.put(tmp_path, scene())
    library.put(tmp_path, broll())
    data = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert data["version"] == 1 and len(data["assets"]) == 2
    assert library.get(library.load(tmp_path), "term-deploy")["kind"] == "broll"


def test_save_refuses_invalid(tmp_path):
    with pytest.raises(ValueError):
        library.save(tmp_path, {"version": 1, "assets": [scene(theme="x")]})
    assert not (tmp_path / "index.json").exists()


def test_missing_files(tmp_path):
    (tmp_path / "tg-coin").mkdir()
    (tmp_path / "tg-coin" / "tg-coin.mp4").write_bytes(b"")
    assert library.missing_files(tmp_path, scene()) == []
    assert library.missing_files(tmp_path, scene(files={"green": "tg-coin/g.mp4"})) == ["green"]


# ── поиск ────────────────────────────────────────────────────────────────────

def test_find_case_and_yo():
    idx = {"version": 1, "assets": [scene(), broll()]}
    assert [e["id"] for e in library.find(idx, "ЕЛКА")] == ["term-deploy"]      # ё → е, регистр
    assert [e["id"] for e in library.find(idx, "глянцевый")] == ["tg-coin"]       # describes
    assert [e["id"] for e in library.find(idx, "Переворот")] == ["tg-coin"]       # событие


def test_find_all_words_must_match():
    idx = {"version": 1, "assets": [scene(), broll()]}
    assert library.find(idx, "терминал команда")[0]["id"] == "term-deploy"
    assert library.find(idx, "терминал переворот") == []


def test_find_filters_and_rank():
    idx = {"version": 1, "assets": [
        scene("a", tags=[], describes="про канал"),
        scene("b", tags=["канал"], describes=""),
        broll(),
    ]}
    assert [e["id"] for e in library.find(idx, "канал")] == ["b", "a"]           # тег весит больше
    assert [e["id"] for e in library.find(idx, kind="broll")] == ["term-deploy"]
    assert [e["id"] for e in library.find(idx, theme="light")] == []
    assert len(library.find(idx)) == 3


# ── стоячие окна ─────────────────────────────────────────────────────────────

def test_usable_windows_cuts_transitions_and_private():
    assert library.usable_windows(broll(), min_len=0.5) == [[0.0, 2.0], [2.4, 6.0], [6.3, 7.0],
                                                            [8.0, 10.0]]


def test_usable_windows_min_len_and_pad():
    assert library.usable_windows(broll(), min_len=1.0) == [[0.0, 2.0], [2.4, 6.0], [8.0, 10.0]]
    assert library.usable_windows(broll(), min_len=0.5, pad=0.1) == [[0.0, 1.9], [2.5, 5.9],
                                                                     [6.4, 6.9], [8.1, 10.0]]
    assert library.usable_windows(broll(), min_len=0.6, pad=0.1) == [[0.0, 1.9], [2.5, 5.9],
                                                                     [8.1, 10.0]]


def test_usable_windows_scene_is_whole():
    assert library.usable_windows(scene()) == [[0.0, 3.3]]


def test_usable_windows_overlapping_cuts():
    e = broll(transitions=[[1.0, 3.0], [2.0, 4.0]], private=[])
    assert library.usable_windows(e, min_len=0.5) == [[0.0, 1.0], [4.0, 10.0]]


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_cli_list_find_show_validate(tmp_path, capsys):
    library.put(tmp_path, scene())
    library.put(tmp_path, broll())
    lib = ["--library", str(tmp_path)]
    assert library.main(["list"] + lib) == 0
    assert "tg-coin" in capsys.readouterr().out
    assert library.main(["find", "клик", "--json"] + lib) == 0
    assert json.loads(capsys.readouterr().out)[0]["id"] == "term-deploy"
    assert library.main(["show", "term-deploy"] + lib) == 0
    out = capsys.readouterr().out
    assert "ПРИВАТНОЕ" in out and "стоячие окна" in out
    assert library.main(["validate"] + lib) == 0       # файлов нет — только предупреждения
    assert "предупреждений" in capsys.readouterr().out


def test_cli_add(tmp_path, capsys):
    p = tmp_path / "entry.json"
    p.write_text(json.dumps(broll(), ensure_ascii=False), encoding="utf-8")
    assert library.main(["add", str(p), "--library", str(tmp_path / "lib")]) == 0
    assert library.get(library.load(tmp_path / "lib"), "term-deploy")
