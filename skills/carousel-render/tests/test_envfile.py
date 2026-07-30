import os

import envfile


def test_parse_reads_pairs():
    got = envfile.parse("THEME_PATH=/a/b.json\nOUTPUT_DIR=/out\n")
    assert got == {"THEME_PATH": "/a/b.json", "OUTPUT_DIR": "/out"}


def test_parse_skips_comments_and_blanks():
    got = envfile.parse("# коммент\n\nA=1\n   # ещё\nB=2\n")
    assert got == {"A": "1", "B": "2"}


def test_parse_strips_quotes():
    assert envfile.parse('A="/путь с пробелом"\n') == {"A": "/путь с пробелом"}
    assert envfile.parse("B='x'\n") == {"B": "x"}


def test_parse_keeps_equals_in_value():
    assert envfile.parse("A=k=v\n") == {"A": "k=v"}


def test_parse_ignores_lines_without_equals():
    assert envfile.parse("мусор\nA=1\n") == {"A": "1"}


def test_load_missing_file_is_quiet(tmp_path):
    assert envfile.load(tmp_path / "нет.env") == {}


def test_load_populates_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("THEME_PATH", raising=False)
    p = tmp_path / ".env"
    p.write_text("THEME_PATH=/tmp/t.json\n", encoding="utf-8")
    assert envfile.load(p) == {"THEME_PATH": "/tmp/t.json"}
    assert os.environ["THEME_PATH"] == "/tmp/t.json"


def test_load_does_not_override_existing(tmp_path, monkeypatch):
    """Разовый прогон `THEME_PATH=… python3 …` не должен перебиваться файлом."""
    monkeypatch.setenv("THEME_PATH", "/явно/задан.json")
    p = tmp_path / ".env"
    p.write_text("THEME_PATH=/из/файла.json\n", encoding="utf-8")
    assert envfile.load(p) == {}
    assert os.environ["THEME_PATH"] == "/явно/задан.json"


def test_load_skips_empty_values(tmp_path, monkeypatch):
    """Незаполненный OUTPUT_DIR в шаблоне не должен превращаться в пустой путь."""
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    p = tmp_path / ".env"
    p.write_text("OUTPUT_DIR=\n", encoding="utf-8")
    assert envfile.load(p) == {}
    assert os.environ.get("OUTPUT_DIR") is None
