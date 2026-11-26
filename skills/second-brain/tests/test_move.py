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


# ── финальное ревью: ни одна заметка не теряется, обычный текст не трогается ──

def _files(root):
    import os
    return sorted(p for p in __import__("vaultlib").iter_files(root) if not p.startswith("_переезд/"))


def test_chain_does_not_overwrite(tmp_path):
    root = tmp_path / "v"
    write(root, "Notes/README.md", "из Notes\n")
    write(root, "wiki/README.md", "старая wiki\n")
    rules_ = [{"from": "Notes/", "to": "wiki/", "why": "", "ask": ""},
              {"from": "wiki/", "to": "archive/old-wiki/", "why": "", "ask": ""}]
    run(root, build(root, rules_), dry=False)
    assert (root / "wiki/README.md").read_text(encoding="utf-8") == "из Notes\n"
    assert (root / "archive/old-wiki/README.md").read_text(encoding="utf-8") == "старая wiki\n"


def test_duplicate_kept_under_original_name(tmp_path):
    root = tmp_path / "v"
    write(root, "Заметка.md", "старая\n")
    write(root, "Заметка (2).md", "свежая\n")
    rules_ = [{"from": "Заметка (2).md", "to": "Заметка.md", "why": "", "ask": ""},
              {"from": "Заметка.md", "to": None, "why": "", "ask": ""}]
    run(root, build(root, rules_), dry=False)
    assert _files(root) == ["Заметка.md"]
    assert (root / "Заметка.md").read_text(encoding="utf-8") == "свежая\n"


def test_collision_refused(tmp_path):
    root = tmp_path / "v"
    write(root, "A/План.md", "а\n"); write(root, "B/План.md", "б\n")
    plan_ = build(root, [{"from": "A/", "to": "wiki/", "why": "", "ask": ""}, {"from": "B/", "to": "wiki/", "why": "", "ask": ""}])
    with pytest.raises(SystemExit, match="одно место"):
        run(root, plan_, dry=False)
    assert _files(root) == ["A/План.md", "B/План.md"]


def test_case_only_collision_refused(tmp_path):
    root = tmp_path / "v"
    write(root, "A/Plan.md", "а\n"); write(root, "B/plan.md", "б\n")
    plan_ = build(root, [{"from": "A/", "to": "wiki/", "why": "", "ask": ""}, {"from": "B/", "to": "wiki/", "why": "", "ask": ""}])
    assert plan_["collisions"] == ["wiki/Plan.md"]
    with pytest.raises(SystemExit, match="одно место"):
        run(root, plan_, dry=False)


def test_prose_tags_urls_untouched(tmp_path):
    root = tmp_path / "v"
    text = "Projects are my focus. #Projects https://github.com/me/Projects [[Projects]] B version\n"
    write(root, "Projects/Сайт/a.md", text)
    write(root, "B/b.md", "b\n")
    write(root, "Bases/x.base", 'filters:\n  - file.inFolder("Projects")\n')
    rules_ = [{"from": "Projects/", "to": "projects/", "why": "", "ask": ""},
              {"from": "B/", "to": "wiki/", "why": "", "ask": ""},
              {"from": "Bases/", "to": "Bases/", "why": "", "ask": ""}]
    run(root, build(root, rules_), dry=False)
    assert (root / "projects/Сайт/a.md").read_text(encoding="utf-8") == text
    assert 'file.inFolder("projects")' in (root / "Bases/x.base").read_text(encoding="utf-8")


def test_folder_path_rewritten_but_not_word_or_url(tmp_path):
    root = tmp_path / "v"
    write(root, "Projects/Сайт/a.md", "папка Projects/Сайт/ — тут; слово Projects; https://x.com/Projects/Сайт\n")
    write(root, "Bases/x.base", 'filters:\n  - file.inFolder("Projects/Сайт")\n')
    rules_ = [{"from": "Projects/", "to": "projects/", "why": "", "ask": ""},
              {"from": "Bases/", "to": "Bases/", "why": "", "ask": ""}]
    run(root, build(root, rules_), dry=False)
    assert (root / "projects/Сайт/a.md").read_text(encoding="utf-8") == \
        "папка projects/Сайт/ — тут; слово Projects; https://x.com/Projects/Сайт\n"
    assert 'file.inFolder("projects/Сайт")' in (root / "Bases/x.base").read_text(encoding="utf-8")
