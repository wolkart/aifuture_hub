import subprocess
import sys

from conftest import KEY, SCRIPTS, TG_TOKEN
from migrate.scan_keys import scan


def test_scan_finds_key(messy_vault):
    hits = [h for h in scan(messy_vault) if not h.placeholder]
    env_hits = [h for h in hits if h.path == ".env"]
    assert {h.line for h in env_hits} == {1, 2}
    for h in hits:
        visible = h.masked.split("…")[0]
        assert len(visible) <= 4


def test_scan_obsidian_plugin(messy_vault):
    assert any(h.path == ".obsidian/plugins/copilot/data.json" and not h.placeholder for h in scan(messy_vault))


def test_scan_telegram_token(messy_vault):
    assert any(h.path == ".env" and h.line == 2 and "telegram" in h.kind for h in scan(messy_vault))


def test_scan_placeholder(messy_vault):
    readme = [h for h in scan(messy_vault) if h.path == "README.md"]
    assert readme and all(h.placeholder for h in readme)


def test_scan_no_content_printed(messy_vault):
    r = subprocess.run([sys.executable, "-I", str(SCRIPTS / "migrate" / "scan_keys.py"), str(messy_vault)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1, r.stderr
    assert KEY not in r.stdout and TG_TOKEN not in r.stdout
    assert ".env:1:" in r.stdout and "похоже на заглушку" in r.stdout
