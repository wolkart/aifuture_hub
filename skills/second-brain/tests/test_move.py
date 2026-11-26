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


# ── находки живого переезда (6 157 файлов) ──

def test_obsidian_plugin_names_untouched(messy_vault, rules):
    write(messy_vault, ".obsidian/plugins/vlozheniya/manifest.json", '{"id": "x", "name": "Вложения"}\n')
    write(messy_vault, ".obsidian/plugins/quickadd/data.json",
          '{"name": "Вложения", "folder": "Вложения", "folders": ["Вложения/старые"]}\n')
    run(messy_vault, build(messy_vault, rules), dry=False)
    assert json.loads((messy_vault / ".obsidian/plugins/vlozheniya/manifest.json").read_text(encoding="utf-8"))["name"] == "Вложения"
    data = json.loads((messy_vault / ".obsidian/plugins/quickadd/data.json").read_text(encoding="utf-8"))
    assert data == {"name": "Вложения", "folder": "files", "folders": ["files/старые"]}


def test_specific_folder_rule_wins_without_slash(messy_vault, rules):
    write(messy_vault, "Ресурсы/Промпты/п.md", "# п\n")
    write(messy_vault, "bases/Промпты.base", 'filters:\n  - file.folder == "Ресурсы/Промпты"\n')
    specific = [{"from": "Ресурсы/Промпты/", "to": "wiki/промпты/", "why": "", "ask": ""}]
    run(messy_vault, build(messy_vault, specific + rules), dry=False)
    assert 'file.folder == "wiki/промпты"' in (messy_vault / "Bases/Промпты.base").read_text(encoding="utf-8")


def test_dry_predicts_without_false_broken(messy_vault, plan):
    write(messy_vault, "0-Входящие/Битая.md", "[[Нет такой]]\n")
    r = run(messy_vault, build(messy_vault, plan["rules"]), dry=True)
    assert r["new_broken"] == []
    assert r["rewritten"] > 0


def test_folder_link_not_new_broken(messy_vault, plan):
    write(messy_vault, "0-Входящие/Ссылка.md", "[[2-Контент/Рилсы]]\n")
    r = run(messy_vault, build(messy_vault, plan["rules"]), dry=False)
    assert r["new_broken"] == []


def test_many_files_fast(tmp_path):
    """Живой переезд: ~12 тыс. пар путей на ~6 тыс. файлов шёл 6 минут — замена не должна зависеть от числа пар."""
    import time
    root = tmp_path / "big"
    for i in range(300):
        write(root, f"Старое/Папка {i % 30}/Заметка {i}.md", f"см. Старое/Папка {(i + 1) % 30}/Заметка {i + 1}.md\n" * 20)
    plan = build(root, [{"from": "Старое/", "to": "wiki/", "why": "", "ask": ""}])
    plan["dest"].update({f"Старое/Нет/Фейк {i}.md": f"wiki/Нет/Фейк {i}.md" for i in range(12000)})
    t0 = time.time()
    r = run(root, plan, dry=False)
    assert r["moved"] == 300
    assert time.time() - t0 < 10
    assert "см. wiki/Папка 2/Заметка 2.md" in (root / "wiki/Папка 1/Заметка 1.md").read_text(encoding="utf-8")
