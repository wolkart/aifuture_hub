"""Публичный хаб: в файлах скилла нет следов автора (путей, имён, проектов)."""
import re
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
FORBIDDEN = [
    "/Users/wolkart", "Артём", "AI Future Club", "content-studio", "hermes-vps",
    "Social Flow", "Yandex.Disk.localized", "com.wolkart",
]
HUB_URL = re.compile(r"(?:codeload\.)?github\.com/wolkart/aifuture_hub")


def skill_files():
    for p in sorted(SKILL.rglob("*")):
        if p.is_file() and "tests" not in p.relative_to(SKILL).parts and "__pycache__" not in p.parts:
            yield p


def test_no_author_traces():
    bad = []
    for p in skill_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        for word in FORBIDDEN:
            if word in text:
                bad.append(f"{p.relative_to(SKILL)}: {word}")
        if "wolkart" in HUB_URL.sub("", text):
            bad.append(f"{p.relative_to(SKILL)}: wolkart вне адреса хаба")
    assert not bad, "\n".join(bad)


def test_skill_has_files():
    assert any(skill_files()), "в скилле нет файлов — проверять нечего"
