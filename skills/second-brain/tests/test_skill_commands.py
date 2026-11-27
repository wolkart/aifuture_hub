"""Команды, которые агент выполняет сам: работают без терминала и на свежем компьютере."""
from conftest import SKILL


def _docs():
    return [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]


def test_rebase_continue_needs_no_editor():
    """У агента нет терминала: голый `git rebase --continue` открывает редактор и падает
    («Terminal is dumb, but EDITOR unset») — конфликт остаётся неразобранным."""
    found = 0
    for doc in _docs():
        for line in doc.read_text(encoding="utf-8").splitlines():
            if "rebase --continue" in line:
                found += 1
                assert "git -c core.editor=true rebase --continue" in line, f"{doc.name}: {line}"
    assert found


def test_second_computer_logs_git_into_github():
    """Без `gh auth setup-git` фоновая задача на втором компьютере не может отправлять, а без имени
    в Git падает ручной разбор конфликта."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    para = text.split("**Второй компьютер.**", 1)[1].split("\n\n", 1)[0]
    assert "setup-git" in para
    assert "имени" in para
