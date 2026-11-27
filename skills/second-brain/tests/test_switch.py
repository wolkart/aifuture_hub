import subprocess
import sys

from conftest import SCRIPTS, write
from migrate.inventory import build
from migrate.switch import run


def test_switch_abs_root(tmp_path):
    f = write(tmp_path, "cfg/.env", "VAULT=/old/vault\nX=/old/vault/x\n")
    assert run([f], "/old/vault", "/new/brain", None, dry=False) == [(str(f), 2, 0)]
    assert f.read_text(encoding="utf-8") == "VAULT=/new/brain\nX=/new/brain/x\n"


def test_switch_with_plan(tmp_path, messy_vault, rules):
    plan = build(messy_vault, rules)
    f = write(tmp_path, "skill/SKILL.md", f"база: {messy_vault}/2-Контент/Рилсы/\nидея: {messy_vault}/0-Входящие/Идея.md\n")
    (_, n, left), = run([f], str(messy_vault), "/new/brain", plan, dry=False)
    text = f.read_text(encoding="utf-8")
    assert "база: /new/brain/content/Рилсы/" in text and "идея: /new/brain/archive/Входящие/Идея.md" in text
    assert left == 0


def test_switch_dry(tmp_path):
    f = write(tmp_path, "a.md", "/old/vault\n")
    assert run([f], "/old/vault", "/new/brain", None, dry=True) == [(str(f), 1, 0)]   # «осталось» — после замены, как в настоящем запуске
    assert f.read_text(encoding="utf-8") == "/old/vault\n"


def test_switch_counts_only(tmp_path):
    f = write(tmp_path, ".env", "SECRET=sk-very-secret-value-123456\nVAULT=/old/vault\n")
    r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "migrate" / "switch.py"), "--old", "/old/vault",
                        "--new", "/new/brain", str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "sk-very-secret" not in r.stdout and "1 замен" in r.stdout


def test_switch_leaves_bare_folders(tmp_path, messy_vault, rules):
    plan = build(messy_vault, rules)
    f = write(tmp_path, "other/state.json", '{"dir": "files/", "x": "2-Контент/чужое"}\n')
    assert run([f], str(messy_vault), "/new/brain", plan, dry=False) == [(str(f), 0, 0)]
    assert f.read_text(encoding="utf-8") == '{"dir": "files/", "x": "2-Контент/чужое"}\n'


def test_switch_left_same_dry_and_real(tmp_path, messy_vault, rules):
    plan = build(messy_vault, rules)
    text = f"{messy_vault}/2-Контент/Рилсы/\n"
    f1, f2 = write(tmp_path, "a.md", text), write(tmp_path, "b.md", text)
    (_, n1, left1), = run([f1], str(messy_vault), "/new/brain", plan, dry=True)
    (_, n2, left2), = run([f2], str(messy_vault), "/new/brain", plan, dry=False)
    assert (n1, left1) == (n2, left2) == (1, 0)


def test_switch_fast_on_big_plan(tmp_path):
    import time
    plan = {"rules": [], "dest": {f"Старое/{i}.md": f"wiki/{i}.md" for i in range(12000)}}
    f = write(tmp_path, "big.log", ("строка лога без путей " * 20 + "\n") * 20000 + "/old/v/Старое/5.md\n")
    t0 = time.time()
    (_, n, left), = run([f], "/old/v", "/new/b", plan, dry=True)
    assert (n, left) == (1, 0)
    assert time.time() - t0 < 10
