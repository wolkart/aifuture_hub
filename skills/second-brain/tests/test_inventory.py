import json
import subprocess
import sys
import unicodedata

from conftest import SCRIPTS
from migrate.inventory import build, render, tree


def test_tree_counts(messy_vault):
    t = tree(messy_vault)
    assert "2-Контент/ — заметок: 1" in t
    assert "Проекты/ — заметок: 2" in t
    assert ".obsidian" not in t


def test_build_first_rule_wins(messy_vault, rules):
    plan = build(messy_vault, [{"from": "2-Контент/Рилсы/", "to": "archive/", "why": "", "ask": ""}] + rules)
    assert plan["dest"]["2-Контент/Рилсы/Рилс про ботов.md"] == "archive/Рилс про ботов.md"


def test_build_folder_rule_keeps_subpath(messy_vault, rules):
    assert build(messy_vault, rules)["dest"]["2-Контент/Рилсы/Рилс про ботов.md"] == "content/Рилсы/Рилс про ботов.md"


def test_build_file_rule_basename(messy_vault, rules):
    assert build(messy_vault, rules)["dest"]["README.md"] == "archive/README.md"


def test_build_exact_target(messy_vault, rules):
    plan = build(messy_vault, [{"from": "README.md", "to": "archive/Старый README.md", "why": "", "ask": ""}] + rules)
    assert plan["dest"]["README.md"] == "archive/Старый README.md"


def test_build_skip_null(messy_vault, rules):
    assert build(messy_vault, rules)["dest"]["Заметка (2).md"] is None


def test_build_unmatched(messy_vault, rules):
    assert build(messy_vault, rules)["unmatched"] == [".env"]


def test_build_collisions(messy_vault, rules):
    plan = build(messy_vault, rules + [{"from": ".env", "to": "wiki/Йога.md", "why": "", "ask": ""}])
    assert plan["collisions"] == ["wiki/Йога.md"]


def test_build_same_name(messy_vault, rules):
    assert build(messy_vault, rules)["same_name"] == {"План.md": ["projects/Бот/План.md", "projects/Сайт/План.md"]}


def test_build_keeps_rules(messy_vault, rules):
    assert build(messy_vault, rules)["rules"] == rules


def test_nfd_paths(messy_vault, rules):
    assert build(messy_vault, rules)["dest"]["Ресурсы/Йога.md"] == "wiki/Йога.md"
    assert all(k == unicodedata.normalize("NFC", k) for k in build(messy_vault, rules)["dest"])


def test_render_questions(messy_vault, rules):
    text = render(build(messy_vault, rules), "2026-11-26")
    q = text[text.index("## Вопросы к тебе"):text.index("## Таблица")]
    assert "**Строка 5.**" in q and "это знание или дневник?" in q
    assert "| 5 | `Заметка.md` | 1 | `wiki/` **?** | знание |" in text
    no_q = [dict(r, ask="") for r in rules]
    text2 = render(build(messy_vault, no_q), "2026-11-26")
    assert "Нет." in text2[text2.index("## Вопросы к тебе"):text2.index("## Таблица")]


def test_render_summary(messy_vault, rules):
    text = render(build(messy_vault, rules), "2026-11-26")
    assert "| `не берём` | 1 | 1 |" in text
    assert "## Без правила" in text and "`.env`" in text


def test_cli_build(messy_vault, rules, tmp_path):
    rp = tmp_path / "rules.json"
    rp.write_text(json.dumps({"rules": rules}, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "migrate" / "inventory.py"), "build", str(messy_vault), str(rp)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    out = messy_vault / "_переезд"
    assert (out / "plan.json").is_file() and (out / "Опись.md").is_file()
    assert "без правила: 1" in r.stdout and "вопросов: 1" in r.stdout


def test_tree_nesting_with_similar_names(tmp_path):
    from conftest import write
    write(tmp_path, "Разведка/автор/a.md"); write(tmp_path, "Разведка YouTube/канал/b.md")
    lines = tree(tmp_path).splitlines()
    assert lines.index("Разведка/ — заметок: 1") + 1 == lines.index("  автор/ — заметок: 1")


def test_dropped_but_linked(messy_vault, rules):
    from conftest import write
    write(messy_vault, "Пустая.md", "")
    write(messy_vault, "Ресурсы/Оглавление.md", "[[Пустая]]\n")
    plan = build(messy_vault, [{"from": "Пустая.md", "to": None, "why": "пустая", "ask": ""}] + rules)
    assert plan["dropped_linked"] == ["Пустая.md"]
    assert "## Не берём, но на них ссылаются" in render(plan, "2026-11-26")


def test_bad_names(messy_vault, rules):
    from conftest import write
    write(messy_vault, "Ресурсы/Qwen .md", "# q\n")
    write(messy_vault, "Ресурсы/�� Штаб.md", "# ш\n")
    plan = build(messy_vault, rules)
    assert plan["bad_names"] == ["Ресурсы/Qwen .md", "Ресурсы/�� Штаб.md"]
    assert "## Подозрительные имена" in render(plan, "2026-11-26")
