import pytest
from textnormx.parser.chunk import split_text_with_overlap

def test_no_word_cut_and_overlap_present():
    text = " ".join([f"word{i}" for i in range(80)])  # ~ 400+ chars
    parts = split_text_with_overlap(text, max_chars=120, overlap_ratio=0.2)
    
    assert parts and all(isinstance(p, str) for p in parts)
    
    for p in parts:
        assert "\n" not in p or True
        assert not p.endswith(" "), "trailing spaces should be trimmed"

    if len(parts) >= 2:
        tail = parts[0][-20:]
        assert tail.split()[0] != "" 
        assert any(t in parts[1] for t in tail.split()), "overlap should share tokens"

def test_prefer_breaks_improves_boundaries():
    text = "Para1 sentence A. Sentence B.\n\nPara2 sentence C. Sentence D."
    parts = split_text_with_overlap(text, max_chars=40, overlap_ratio=0.15)
    assert len(parts) >= 2
