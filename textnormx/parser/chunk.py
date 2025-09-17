from __future__ import annotations
import uuid
from typing import List
from .types import Element, Chunk

__all__ = ["chunk_by_title"]

def chunk_by_title(
    elements: List[Element],
    *,
    filename: str = "document.md",
    filetype: str = "md",
    last_modified: str | None = None,
    chunk_size: int = 500,
    min_chunk_chars: int = 40,
) -> List[Chunk]:
    """
    Aggregate consecutive Text elements under the most recent Title, then split the
    aggregated text into ~chunk_size character chunks with soft breaks.
    Tables are emitted as dedicated chunks (not mixed into text).
    Returns Chunk objects with metadata (filename, filetype, page_number, parent_id, ...).
    """
    sections = []
    cur_title = None
    cur_title_id = None
    buf: list[str] = []
    pg_start = pg_end = None

    def flush():
        """Push the current text buffer as a section (if any) and reset the buffer."""
        nonlocal buf, cur_title, cur_title_id, pg_start, pg_end
        if not buf:
            return
        txt = "\n".join(buf).strip()
        if txt:
            sections.append({
                "title": cur_title,
                "title_id": cur_title_id,
                "text": txt,
                "page_start": pg_start or 1,
                "page_end": pg_end or pg_start or 1,
            })
        buf = []

    NAMESPACE = uuid.NAMESPACE_URL
    chunks: List[Chunk] = []

    # Build sections: collect Text under the latest Title; emit Tables immediately
    for e in elements:
        if e.type == "Title":
            flush()
            cur_title = e.text
            cur_title_id = str(uuid.uuid4())
            pg_start = pg_end = e.page or 1

        elif e.type == "Text":
            t = (e.text or "").strip()
            if not t:
                continue
            p = e.page or 1
            pg_start = p if pg_start is None else min(pg_start, p)
            pg_end   = p if pg_end   is None else max(pg_end,   p)
            buf.append(t)

        elif e.type == "Table":
            # Do NOT mix tables into the text buffer → emit a dedicated chunk now
            flush()
            tbl_id = str(uuid.uuid5(
                NAMESPACE, f"{filename}:table:{e.page}:{hash(e.text) & 0xffffffff}"
            ))
            chunks.append(Chunk(
                text=e.text,
                element_id=tbl_id,
                type="Table",
                metadata={
                    "filename": filename,
                    "filetype": filetype,
                    "last_modified": last_modified,
                    "page_number": int(e.page or 1),
                    "parent_id": cur_title_id,  # link to current section (if any)
                    "coordinates": None,
                },
            ))

    flush()

    # Split each section's text into chunks with soft boundaries and merge tiny tails
    for si, s in enumerate(sections):
        t = s["text"]
        start = 0
        local: List[Chunk] = []
        ci = 0

        while start < len(t):
            end = min(start + chunk_size, len(t))
            piece = t[start:end]

            # Soft cut: prefer to break on paragraph or sentence boundary
            cut = max(piece.rfind("\n\n"), piece.rfind(". "))
            if cut > int(chunk_size * 0.6):
                end = start + cut + 1
                piece = t[start:end]

            piece = piece.strip()
            if not piece:
                start = end
                continue

            if local and len(piece) < min_chunk_chars:
                # Merge very short tail into the previous chunk
                prev = local[-1]
                prev.text = (prev.text.rstrip() + " " + piece).strip()
            else:
                chunk_id = str(uuid.uuid5(
                    NAMESPACE, f"{filename}:{s['page_start']}:{si}:{ci}:{piece[:64]}"
                ))
                local.append(Chunk(
                    text=piece,
                    element_id=chunk_id,
                    type="Text",
                    metadata={
                        "filename": filename,
                        "filetype": filetype,
                        "last_modified": last_modified,
                        "page_number": int(s["page_start"]),
                        "parent_id": s["title_id"],
                        "coordinates": None,
                    },
                ))
                ci += 1

            start = end

        chunks.extend(local)

    return chunks
