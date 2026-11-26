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
    assert run([f], "/old/vault", "/new/brain", None, dry=True) == [(str(f), 1, 1)]
    assert f.read_text(encoding="utf-8") == "/old/vault\n"


def test_switch_counts_only(tmp_path):
    f = write(tmp_path, ".env", "SECRET=sk-very-secret-value-123456\nVAULT=/old/vault\n")
    r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "migrate" / "switch.py"), "--old", "/old/vault",
                        "--new", "/new/brain", str(f)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "sk-very-secret" not in r.stdout and "1 замен" in r.stdout
