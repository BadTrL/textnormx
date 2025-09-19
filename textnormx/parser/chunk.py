# textnormx/parser/chunk.py
from __future__ import annotations

import re
import uuid
from typing import List, Optional

from .types import Element, Chunk

# Tokenizer that captures a "word + following spaces".
# This lets us pack chunks by characters without cutting inside words.
_WORD_PIECES = re.compile(r"\S+\s*")


def split_text_with_overlap(
    text: str,
    max_chars: int = 500,
    *,
    overlap_chars: int | None = None,
    overlap_ratio: float = 0.10,
    prefer_breaks: tuple[str, ...] = ("\n\n", "\n", ". ", "? ", "! "),
    keep_delimiters: bool = True,
) -> list[str]:
    """
    Split `text` into ~max_chars windows without cutting inside words, and add
    an overlap between consecutive windows. Tries to end near "nice" boundaries
    (paragraph breaks, sentence ends) when possible.

    Args:
        text: Input string to split.
        max_chars: Target maximum characters per window.
        overlap_chars: Fixed overlap size in characters (if provided, overrides overlap_ratio).
        overlap_ratio: Fraction of `max_chars` to overlap between consecutive windows.
        prefer_breaks: Ordered list of delimiters to prefer for cuts near the end of a window.
        keep_delimiters: If True, keep the delimiter at the end of the first piece.

    Returns:
        List of window strings with soft boundaries and overlap.
    """
    if not text:
        return []

    # Compute overlap in characters
    ov = overlap_chars if overlap_chars is not None else int(max_chars * overlap_ratio)
    ov = max(0, min(ov, max_chars - 1))

    pieces = _WORD_PIECES.findall(text)
    chunks: list[str] = []
    cur = 0

    while cur < len(pieces):
        start = cur
        size = 0
        buf: list[str] = []

        # Greedily pack tokens while respecting max_chars
        while cur < len(pieces) and size + len(pieces[cur]) <= max_chars:
            buf.append(pieces[cur])
            size += len(pieces[cur])
            cur += 1

        joined = "".join(buf)
        if joined:
            # Try to cut near a preferred delimiter close to the end
            cut = len(joined)
            for delim in prefer_breaks:
                idx = joined.rfind(delim)
                # If a delimiter is found close to the end, cut there
                if idx != -1 and idx >= max_chars - 120:
                    cut = idx + (len(delim) if keep_delimiters else 0)
                    break

            if cut < len(joined):
                leftover = joined[cut:]
                joined = joined[:cut]
                # Re-inject the leftover into the token stream for the next window
                if leftover:
                    pieces[cur:cur] = _WORD_PIECES.findall(leftover)

            chunks.append(joined.rstrip())

        # Apply overlap by stepping back ~ov characters worth of tokens
        if ov > 0 and cur < len(pieces):
            back = 0
            acc = 0
            while back < (cur - start) and acc < ov:
                back += 1
                acc += len(pieces[cur - back])
            cur = max(start, cur - back)

    return chunks


def chunk_by_title(
    elements: List[Element],
    *,
    filename: str = "document.md",
    filetype: str = "md",
    last_modified: Optional[str] = None,
    chunk_size: int = 500,
    min_chunk_chars: int = 40,
    overlap_ratio: float = 0.10,
) -> List[Chunk]:
    """
    Aggregate consecutive Text elements under the most recent Title, then split
    each aggregated block into ~chunk_size windows with word-safe overlap.
    Tables are emitted as dedicated Table chunks and are not mixed into text.

    Args:
        elements: Linear list of parsed elements (Title / Text / Table).
        filename: Source filename for metadata.
        filetype: Source filetype for metadata (e.g., "md").
        last_modified: Optional last-modified timestamp for metadata.
        chunk_size: Target maximum characters per text chunk.
        min_chunk_chars: If the last window of a section is tiny, merge it into the previous one.
        overlap_ratio: Fraction of `chunk_size` to overlap between consecutive text chunks.

    Returns:
        List[Chunk]: ready-to-embed chunks with metadata
            - Text chunks have `parent_id` referencing the section (Title) UUID.
            - Table chunks have `parent_id=None`.
    """
    sections: List[dict] = []
    cur_title: Optional[str] = None
    cur_title_id: Optional[str] = None
    buf: List[str] = []
    pg_start: Optional[int] = None
    pg_end: Optional[int] = None

    def flush() -> None:
        """Push the current text buffer as a section and reset the buffer."""
        nonlocal buf, cur_title, cur_title_id, pg_start, pg_end
        if not buf:
            return
        txt = "\n".join(buf).strip()
        if txt:
            sections.append(
                {
                    "title": cur_title,
                    "title_id": cur_title_id,
                    "text": txt,
                    "page_start": pg_start or 1,
                    "page_end": pg_end or pg_start or 1,
                }
            )
        buf.clear()
        pg_start = None
        pg_end = None

    chunks: List[Chunk] = []

    # Pass 1: Build sections and emit tables immediately
    for e in elements:
        if e.type == "Title":
            flush()
            cur_title = (e.text or "").strip() or None
            cur_title_id = str(uuid.uuid4())
            pg_start = pg_end = e.page or 1

        elif e.type == "Table":
            table_txt = (e.text or "").strip()
            if table_txt:
                chunks.append(
                    Chunk(
                        text=table_txt,
                        element_id=str(uuid.uuid4()),
                        type="Table",
                        metadata={
                            "filename": filename,
                            "filetype": filetype,
                            "last_modified": last_modified,
                            "page_number": e.page or 1,
                            "parent_id": None,  # tables are not attached to a title
                            "coordinates": None,
                        },
                    )
                )

        elif e.type == "Text":
            t = (e.text or "").strip()
            if not t:
                continue
            p = e.page or 1
            pg_start = p if pg_start is None else min(pg_start, p)
            pg_end = p if pg_end is None else max(pg_end, p)
            buf.append(t)

        else:
            # Unknown types: ignore (or treat as Text if desired)
            continue

    flush()

    # Pass 2: Split each text section into overlapped chunks
    for sec in sections:
        text = sec["text"]
        if not text:
            continue

        windows = split_text_with_overlap(
            text,
            max_chars=chunk_size,
            overlap_ratio=overlap_ratio,
        )

        # Merge tiny tail into the previous chunk to avoid micro-chunks
        if len(windows) >= 2 and len(windows[-1]) < min_chunk_chars:
            windows[-2] = (windows[-2].rstrip() + "\n" + windows[-1]).strip()
            windows.pop()

        for w in windows:
            chunks.append(
                Chunk(
                    text=w.rstrip(),
                    element_id=str(uuid.uuid4()),
                    type="Text",
                    metadata={
                        "filename": filename,
                        "filetype": filetype,
                        "last_modified": last_modified,
                        "page_number": sec["page_start"],
                        "parent_id": sec["title_id"],  # link to the section (Title)
                        "coordinates": None,
                    },
                )
            )

    return chunks
