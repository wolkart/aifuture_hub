"""Windows PowerShell 5.1 читает .ps1 без BOM в кодировке системы — кириллица превращается в мусор."""
from conftest import SKILL


def test_ps1_have_utf8_bom():
    files = sorted(SKILL.rglob("*.ps1"))
    assert files
    bad = [str(p.relative_to(SKILL)) for p in files if not p.read_bytes().startswith(b"\xef\xbb\xbf")]
    assert not bad, bad


def test_no_binary_pipe_in_powershell():
    """Windows PowerShell 5.1 перекодирует байты в конвейере между программами — архив из curl.exe | tar портится."""
    import re
    text = (SKILL / "references" / "windows.md").read_text(encoding="utf-8")
    code = "\n".join(re.findall(r"```powershell\n(.*?)```", text, re.S))
    assert "curl.exe" in code and "| tar" not in code
