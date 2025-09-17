from __future__ import annotations
import re, sys, unicodedata
from typing import Dict, Iterable, List
from .mappings import PUA_BULLETS, TRANSLATE_MAP

# Regex pre-compiled
RE_PUA = re.compile(r"[\uE000-\uF8FF]")          # Private Use Area
RE_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")  # delete \t \n
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
) -> str:
    """clean string : PUA bullets, quotes/dashes, NBSP, contrôle, ToC, etc."""
    if not s:
        return s
    # 1) Simple replacement + Unicode normalisation
    s = _translate_basic(s)
    s = unicodedata.normalize(normalize_form, s)

    # 2) delete residual PUA (unmapped)
    if drop_pua_rest:
        s = RE_PUA.sub("", s)

    # 3) per lign : harmonizing list heads, drop ToC lines
    out_lines: List[str] = []
    for ln in s.splitlines():
        if strip_toc_lines and RE_TOC_LINE.search(ln.strip()):
            continue
        ln = RE_LIST_HEAD.sub(f"{bullet} ", ln) 
        out_lines.append(ln)

    s = "\n".join(out_lines)

    # 4) delete control chars
    s = RE_CTRL.sub("", s)

    # 5) collapse whitespace
    if collapse_ws:
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r" ?\n ?", "\n", s)
        s = s.strip()

    return s

def clean_lines(lines: Iterable[str], **kwargs) -> List[str]:
    """ Clean a list of lines. """
    return [clean_text(x, **kwargs) for x in lines]

def clean_chunks(
    chunks: List[Dict[str, object]],
    text_key: str = "text",
    in_place: bool = True,
    **kwargs,
) -> List[Dict[str, object]]:
    """
    Clean a list of dicts containing text under `text_key`.
    """
    target = chunks if in_place else [dict(c) for c in chunks]
    for c in target:
        t = c.get(text_key, "")
        if isinstance(t, str):
            c[text_key] = clean_text(t, **kwargs)
    return target

# ---- CLI ----
def main(argv: List[str] | None = None) -> None:
    """Usage:
        echo "Texte \uf0b7 test" | textnormx
        textnormx < infile.txt > outfile.txt
    """
    data = sys.stdin.read()
    sys.stdout.write(clean_text(data))
