import json
import os

import pytest

from conftest import write
from migrate.inventory import build
from migrate.move import run


def listing(root):
    return sorted(os.listdir(root))


@pytest.fixture
def plan(messy_vault, rules):
    return build(messy_vault, rules)


def test_dry_changes_nothing(messy_vault, plan):
    before = sorted(p for p, _, _ in os.walk(messy_vault))
    r = run(messy_vault, plan, dry=True)
    assert r["moved"] > 0
    assert sorted(p for p, _, _ in os.walk(messy_vault)) == before


def test_moves_files(messy_vault, plan):
    run(messy_vault, plan, dry=False)
    assert (messy_vault / "content/Рилсы/Рилс про ботов.md").is_file()
    assert (messy_vault / "projects/Сайт/План.md").is_file()
    assert (messy_vault / "wiki/Йога.md").is_file()
    assert not (messy_vault / "2-Контент").exists() and not (messy_vault / "0-Входящие").exists()
    assert (messy_vault / ".env").is_file()   # без правила — остаётся на месте


def test_skip_removed(messy_vault, plan):
    r = run(messy_vault, plan, dry=False)
    assert r["skipped"] == 1
    assert not (messy_vault / "Заметка (2).md").exists()


def test_case_only_rename(messy_vault, plan):
    run(messy_vault, plan, dry=False)
    assert "Bases" in listing(messy_vault) and "bases" not in listing(messy_vault)
    assert (messy_vault / "Bases/Контент.base").is_file()


def test_rewrites_paths_in_text(messy_vault, plan):
    run(messy_vault, plan, dry=False)
    text = (messy_vault / "content/Рилсы/Рилс про ботов.md").read_text(encoding="utf-8")
    assert "файл: content/Рилсы/Рилс про ботов.md" in text


def test_rewrites_base_filter(messy_vault, plan):
    run(messy_vault, plan, dry=False)
    assert 'file.inFolder("content")' in (messy_vault / "Bases/Контент.base").read_text(encoding="utf-8")


def test_obsidian_settings(messy_vault, plan):
    r = run(messy_vault, plan, dry=False)
    app = json.loads((messy_vault / ".obsidian/app.json").read_text(encoding="utf-8"))
    assert app["attachmentFolderPath"] == "files"
    assert ".obsidian/app.json" in r["obsidian"]


def test_no_new_broken_links(messy_vault, plan):
    r = run(messy_vault, plan, dry=False)
    assert r["new_broken"] == []


def test_rename_updates_links(messy_vault, rules):
    write(messy_vault, "Ресурсы/Про README.md", "[[README]] и [[README|описание]]\n")
    plan = build(messy_vault, [{"from": "README.md", "to": "archive/Старый README.md", "why": "", "ask": ""}] + rules)
    r = run(messy_vault, plan, dry=False)
    text = (messy_vault / "wiki/Про README.md").read_text(encoding="utf-8")
    assert "[[Старый README]] и [[Старый README|описание]]" in text
    assert r["new_broken"] == []


def test_occupied_target_stops(messy_vault, rules):
    write(messy_vault, "content/Рилсы/Рилс про ботов.md", "уже здесь\n")
    plan = build(messy_vault, rules)
    with pytest.raises(SystemExit, match="занято"):
        run(messy_vault, plan, dry=False)
    assert (messy_vault / "2-Контент/Рилсы/Рилс про ботов.md").is_file()
    assert (messy_vault / "Проекты/Сайт/План.md").is_file()


def test_root_note_name_not_rewritten_in_prose(messy_vault, plan):
    run(messy_vault, plan, dry=False)
    assert (messy_vault / "wiki/Заметка.md").read_text(encoding="utf-8") == "# Заметка\n"
    assert "[[Заметка]]" in (messy_vault / "wiki/Йога.md").read_text(encoding="utf-8")
