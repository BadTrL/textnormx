from textnormx import clean_text, clean_chunks

def test_bullet_pua_to_dash():
    s = " \uf0b7 Item 1\n\uf0b7  Item 2"
    out = clean_text(s, bullet="-")
    assert out.splitlines()[0].startswith("- ")
    assert "- Item 2" in out

def test_quotes_dashes_nbsp():
    s = "“Bonjour” — test\u00A0!"
    out = clean_text(s)
    assert '"Bonjour" - test !' in out

def test_chunks_list():
    chunks = [{"text": "\uf0b7 Eggs"}, {"text": "Plain line"}]
    clean_chunks(chunks)
    assert chunks[0]["text"].startswith("• ") or chunks[0]["text"].startswith("- ")

def test_strip_toc():
    s = "Breakfast.................4\nKeep\nLunch...............8"
    out = clean_text(s)
    assert "Keep" in out and "Breakfast" not in out and "Lunch" not in out
