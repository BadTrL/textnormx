import pytest
detect = pytest.importorskip("textnormx.parser.types").detect_format  

def test_detect_html_vs_md():
    assert detect("<html><body><p>Hi</p></body></html>") == "html"
    assert detect("# Title\n\nSome text") == "md"
    assert detect("Just plain text") in {"plain", "md"}