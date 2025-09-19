from textnormx.cleaner.normalize import clean_text, clean_lines, clean_chunks
from textnormx.parser.types import Chunk
from textnormx.cleaner.normalize import normalize_extracted_text

def test_clean_text_preserves_md_table():
    s = "| A |  B |\n| -- | -- |\n| 1  |  2 |"
    out = clean_text(s, preserve_markdown_tables=True)
    assert "| A |  B |" in out  # spacing preserved
    assert "\u00A0" not in out

def test_clean_lines_basic():
    lines = ["\uf0b7 bullet", "plain"]
    out = clean_lines(lines)
    assert "-" in out[0] and "\uf0b7" not in out[0]
    assert out[1] == "plain"

def test_clean_chunks_dataclass_and_md_table():
    ch = Chunk(
        text="A \uf0b7 bullet\n| C1 | C2 |\n| -- | -- |",
        element_id="id", type="Text",
        metadata={"filename":"f","filetype":"md","page_number":1,"parent_id":None,"coordinates":None},
    )
    clean_chunks([ch], preserve_markdown_tables=True)
    assert "-" in ch.text and "\uf0b7" not in ch.text
    assert "| C1 | C2 |" in ch.text

def test_unescape_and_strip_glyph_runs():
    s = "&gt;Hello glyph<c=3,font=/Arial>World&lt;"
    out = normalize_extracted_text(s)
    assert out.startswith(">Hello ")
    assert "glyph<" not in out
    assert out.endswith("World<")

def test_caesar_fix_typical_minus3():
    # "PERSONAL DATA SHALL NOT BE TRANSFERRED" shift +3 -> SHUVRQDO DATA VKDOO ...
    shifted = "SHUVRQDO DATA VKDOO QRW EH WUDQVIHUUHG"
    out = normalize_extracted_text(shifted)
    # Heuristic fix should bring "PERSONAL" back or at least greatly improve
    assert "PERSONAL" in out or "personal" in out.lower()

def test_noop_when_clean():
    s = "Regular text without artifacts."
    out = normalize_extracted_text(s)
    assert out == s

def test_empty_is_safe():
    assert normalize_extracted_text("") == ""
    assert normalize_extracted_text(None) == None
