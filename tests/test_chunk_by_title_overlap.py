import pytest
from textnormx.parser.types import Element
from textnormx.parser.chunk import chunk_by_title

def test_chunk_by_title_tables_and_text_overlap():
    elems = [
        Element(type="Title", text="Section 1", page=1),
        Element(type="Text",  text="Para one. " * 10, page=1),
        Element(type="Table", text="| H1 | H2 |\n| -- | -- |\n| A  | B  |", page=1),
        Element(type="Text",  text="Para two continues here. " * 12, page=1),
        Element(type="Title", text="Section 2", page=2),
        Element(type="Text",  text="Another long paragraph " * 15, page=2),
    ]

    chunks = chunk_by_title(
        elems,
        filename="sample.md",
        filetype="md",
        chunk_size=120,
        min_chunk_chars=30,
        overlap_ratio=0.15,
    )

    assert any(c.type == "Table" for c in chunks)
    assert any(c.type == "Text" for c in chunks)

    for c in chunks:
        if c.type == "Text":
            assert c.metadata.get("parent_id"), "Text chunks should be attached to a title"

    for c in chunks:
        if c.type == "Table":
            assert c.metadata.get("parent_id") is None

    section1_texts = [c for c in chunks if c.type == "Text" and c.metadata["page_number"] == 1]
    if len(section1_texts) >= 2:
        tail = section1_texts[0].text[-20:]
        assert any(tok and tok in section1_texts[1].text for tok in tail.split()), "Expected overlap between consecutive chunks"
