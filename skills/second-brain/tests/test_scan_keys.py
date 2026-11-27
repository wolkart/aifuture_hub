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


def test_scan_no_false_sk_in_words(tmp_path):
    from conftest import write
    write(tmp_path, "a.md", "task-list-item, -webkit-mask-image, elon-musk-says-hello-world-long\n")
    assert scan(tmp_path) == []


def test_scan_more_formats(tmp_path):
    from conftest import write
    write(tmp_path, "k.md", "hf_" + "Ab3" * 10 + "\npplx-" + "Zx9" * 10 + "\nsk_" + "a1b2" * 12 + "\ngsk_" + "Q7w" * 10 + "\n")
    kinds = {h.kind for h in scan(tmp_path) if not h.placeholder}
    assert {"huggingface", "perplexity", "elevenlabs/stripe", "groq"} <= kinds


def test_scan_skips_plugin_code(tmp_path):
    from conftest import write
    write(tmp_path, ".obsidian/plugins/x/main.js", 'var a="sk-' + "q" * 40 + '";\n')
    write(tmp_path, ".obsidian/plugins/x/data.json", '{"apiKey": "sk-' + "r1" * 20 + '"}\n')
    assert [h.path for h in scan(tmp_path)] == [".obsidian/plugins/x/data.json"]
