"""Windows PowerShell 5.1 читает .ps1 без BOM в кодировке системы — кириллица превращается в мусор."""
from conftest import SKILL


def test_ps1_have_utf8_bom():
    files = sorted(SKILL.rglob("*.ps1"))
    assert files
    bad = [str(p.relative_to(SKILL)) for p in files if not p.read_bytes().startswith(b"\xef\xbb\xbf")]
    assert not bad, bad
