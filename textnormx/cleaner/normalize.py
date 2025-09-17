from __future__ import annotations
import re, sys, unicodedata
from typing import Iterable, List
from .mappings import PUA_BULLETS, TRANSLATE_MAP

# Regex pre-compiled
RE_PUA = re.compile(r"[\uE000-\uF8FF]")          # Private Use Area
RE_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")  # keep \t(0x09), \n(0x0A), \r(0x0D)
RE_TOC_LINE = re.compile(r"\.{3,}\s*\d+\s*$")    # "....... 23"
RE_LIST_HEAD = re.compile(r"^\s*(?:•|\*|·|∙|‧|■|▪|●|◦|—|-)\s*")

def _translate_basic(s: str) -> str:
    # remap PUA bullets -> '•'
    if any(ch in s for ch in PUA_BULLETS):
        for ch in PUA_BULLETS:
            s = s.replace(ch, "•")
    # remap divers (dashes, quotes, NBSP)
    return s.translate(str.maketrans(TRANSLATE_MAP))

def clean_text(
    s: str,
    *,
    bullet: str = "-",
    drop_pua_rest: bool = True,
    normalize_form: str = "NFKC",
    collapse_ws: bool = True,
    strip_toc_lines: bool = True,
    preserve_markdown_tables: bool = True,
) -> str:
    """Clean string: PUA bullets, quotes/dashes, NBSP, control chars, ToC lines, etc.
    If preserve_markdown_tables=True, do not aggressively collapse whitespace on lines
    that look like Markdown tables (starting with '|' and containing another '|').
    """
    if not s:
        return s

    # 1) Basic replacements + Unicode normalization
    s = _translate_basic(s)
    s = unicodedata.normalize(normalize_form, s)

    # 2) Drop residual PUA (unmapped)
    if drop_pua_rest:
        s = RE_PUA.sub("", s)

    # 3) Per-line cleanup: normalize list heads, drop ToC lines
    out_lines: List[str] = []
    for ln in s.splitlines():
        if strip_toc_lines and RE_TOC_LINE.search(ln.strip()):
            continue
        ln = RE_LIST_HEAD.sub(f"{bullet} ", ln)
        out_lines.append(ln)
    s = "\n".join(out_lines)

    # 4) Remove control characters (keeps \t \n \r)
    s = RE_CTRL.sub("", s)

    # 5) Collapse whitespace (preserving Markdown tables if requested)
    if collapse_ws:
        if preserve_markdown_tables:
            new_lines: List[str] = []
            for ln in s.splitlines():
                is_table = ln.lstrip().startswith("|") and ("|" in ln.lstrip()[1:])
                if is_table:
                    # Keep table spacing as-is; trim trailing spaces only
                    new_lines.append(ln.rstrip())
                else:
                    ln = re.sub(r"[ \t]+", " ", ln)
                    new_lines.append(ln.strip())
            s = "\n".join(new_lines)
        else:
            s = re.sub(r"[ \t]+", " ", s)
            # normalize spaces around newlines
            s = re.sub(r" ?\n ?", "\n", s)
            s = s.strip()

    return s

def clean_lines(lines: Iterable[str], **kwargs) -> List[str]:
    """ Clean a list of lines. """
    return [clean_text(x, **kwargs) for x in lines]

def _get_text_field(obj, key: str = "text") -> str:
    if isinstance(obj, dict):
        return obj.get(key, "")
    return getattr(obj, key, "")

def _set_text_field(obj, value: str, key: str = "text") -> None:
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)

def clean_chunks(
    chunks,
    *,
    text_key: str = "text",
    bullet: str = "-",
    preserve_markdown_tables: bool = True,
    in_place: bool = True,
):
    """
    Clean the 'text' field of a list of chunks in-place.
    Works with both dict-based chunks and object/dataclass chunks.

    Args:
        chunks: iterable of dicts or objects having a 'text' attribute.
        text_key: field name to clean when chunks are dicts.
        bullet: replacement for PUA bullets, etc.
        preserve_markdown_tables: avoid altering '|' and table syntax.
        in_place: keep original objects (True) or return shallow-copied cleaned chunks.

    Returns:
        The same list (if in_place=True) or a new list with cleaned chunks.
    """
    if not in_place:
        cleaned = []

    for c in chunks:
        t = _get_text_field(c, text_key) or ""
        t2 = clean_text(t, bullet=bullet, preserve_markdown_tables=preserve_markdown_tables)

        if in_place:
            _set_text_field(c, t2, text_key)
        else:
            if isinstance(c, dict):
                nc = dict(c)
                nc[text_key] = t2
            else:
                from copy import copy
                nc = copy(c)
                setattr(nc, text_key, t2)
            cleaned.append(nc)

    return chunks if in_place else cleaned

# ---- CLI ----
def main(argv: List[str] | None = None) -> None:
    """Usage:
        echo "Texte \uf0b7 test" | textnormx
        textnormx < infile.txt > outfile.txt
    """
    data = sys.stdin.read()
    sys.stdout.write(clean_text(data))
