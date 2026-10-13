import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
for p in (SKILL / "scripts", SKILL / "templates", SKILL.parent / "reel" / "scripts"):
    sys.path.insert(0, str(p))

import settings  # noqa: E402


@pytest.fixture
def theme():
    return settings.default()["theme"]


@pytest.fixture
def fake_gsap(tmp_path, monkeypatch):
    """GSAP не нужен для сборки проекта без рендера — подставляем пустышку вместо кеша/npm."""
    import hf
    p = tmp_path / "gsap.min.js"
    p.write_text("/* gsap stub */", encoding="utf-8")
    monkeypatch.setattr(hf, "ensure_gsap", lambda: p)
    return p
