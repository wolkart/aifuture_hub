"""Скрипты запускаются так, как их запускает агент: python3 -I <скрипт> <мозг>."""
import subprocess
import sys

from conftest import SCRIPTS, write


def run(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def test_links_cli_clean(vault):
    r = run("links.py", vault)
    assert r.returncode == 0, r.stderr
    assert "битых ссылок: 0" in r.stdout


def test_links_cli_broken(vault):
    write(vault, "wiki/А.md", "[[Нет]]\n")
    r = run("links.py", vault)
    assert r.returncode == 1, r.stderr
    assert "wiki/А.md → Нет" in r.stdout


def test_cards_cli(vault):
    r = run("cards.py", vault)
    assert r.returncode == 0, r.stderr
    assert "Сайт студии: ссылок 2" in r.stdout
