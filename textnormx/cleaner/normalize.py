# textnormx/cleaner/normalize.py
from __future__ import annotations

import re
import sys
import unicodedata
from html import unescape
from typing import Iterable, List

from .mappings import PUA_BULLETS, TRANSLATE_MAP

# --- Public exports ----------------------------------------------------------

__all__ = [
    "normalize_extracted_text",
    "clean_text",
    "clean_lines",
    "clean_chunks",
]

# --- Pre-compiled regexes ----------------------------------------------------

# Unicode Private Use Area (BMP)
RE_PUA = re.compile(r"[\uE000-\uF8FF]")

# Control chars except TAB(0x09), LF(0x0A), CR(0x0D)
RE_CTRL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Table-of-contents lines like "....... 23"
RE_TOC_LINE = re.compile(r"\.{3,}\s*\d+\s*$")

# Normalize list bullets at line start
RE_LIST_HEAD = re.compile(r"^\s*(?:•|\*|·|∙|‧|■|▪|●|◦|—|-)\s*")

# Extractor artefacts like: glyph<...>
GLYPH_RUN_RE = re.compile(r"glyph<[^>]*>")

# Heuristic trigger: ALL-CAPS words (≥4 letters)
CAPS_WORD_RE = re.compile(r"\b[A-Z]{4,}\b")

# Extra artefacts frequently seen in extracted text
RE_ZERO_WIDTH = re.compile(r"[\u200B-\u200D\u2060]")  # ZWSP/ZWNJ/ZWJ/WORD JOINER
RE_SOFT_HYPHEN = re.compile(r"\u00AD")
RE_BOM = re.compile(r"\ufeff")
RE_VARIATION_SELECTORS = re.compile(r"[\uFE00-\uFE0F]")

# --- Language-agnostic artefact stripping -----------------------------------

def _strip_extraction_artifacts(s: str) -> str:
    """
    Language-agnostic cleanup for OCR/PDF/HTML extraction artefacts:
    - HTML entity unescape
    - Remove ad-hoc glyph runs
    - Normalize bullets and punctuation via TRANSLATE_MAP / PUA_BULLETS
    - Unicode normalization (NFKC)
    - Drop PUA leftovers, zero-width characters, soft hyphens, BOM, variation selectors
    - Remove control characters (keep \t \n \r)
    """
    if not s:
        return s

    # Decode HTML entities (e.g., &nbsp;)
    s = unescape(s)

    # Remove extractor-specific glyph runs
    s = GLYPH_RUN_RE.sub("", s)

    # Remap PUA bullets to a canonical bullet
    if any(ch in s for ch in PUA_BULLETS):
        for ch in PUA_BULLETS:
            s = s.replace(ch, "•")

    # Normalize punctuation/dashes/quotes/NBSP via mapping
    s = s.translate(str.maketrans(TRANSLATE_MAP))

    # Unicode normalization: compatibility form handles ligatures/fullwidth
    s = unicodedata.normalize("NFKC", s)

    # Strip residual artefacts
    s = RE_PUA.sub("", s)
    s = RE_ZERO_WIDTH.sub("", s)
    s = RE_SOFT_HYPHEN.sub("", s)
    s = RE_BOM.sub("", s)
    s = RE_VARIATION_SELECTORS.sub("", s)

    # Drop disallowed control chars
    s = RE_CTRL.sub("", s)

    return s

# --- Optional Caesar (ROT-N) fix, token-based and conservative ---------------

try:
    # Optional dependency; if missing we fall back to a heuristic
    from wordfreq import zipf_frequency as _zipf  # type: ignore
except Exception:
    _zipf = None  # type: ignore[assignment]

_VOWELS = set("aeiou")
_COMMON_BIGRAMS = ("th", "he", "in", "er", "an", "re", "on", "at", "en")
_CAPS_TOKEN_RE = re.compile(r"[A-Z]{4,}")

def _english_token_score(token: str) -> float:
    """
    Score how “English-like” a token is.
    - With wordfreq: return Zipf frequency (≈0..7+, higher is more common).
    - Fallback: 0..2 based on vowel ratio and presence of frequent bigrams.
    """
    t = token.lower()
    if _zipf:
        return _zipf(t, "en")

    letters = "".join(ch for ch in t if ch.isalpha())
    if not letters:
        return 0.0

    vr = sum(ch in _VOWELS for ch in letters) / len(letters)
    bigrams = sum(bg in t for bg in _COMMON_BIGRAMS)
    score = 0.0
    if 0.25 <= vr <= 0.55:
        score += 1.0
    if bigrams >= 1:
        score += 1.0
    return score

def _caesar_shift_token(tok: str, k: int) -> str:
    """
    Decode a single ALL-CAPS token by shifting letters backward by k.
    Non-letters are preserved (though tokens are expected to be A–Z).
    """
    out = []
    for ch in tok:
        if "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 - k) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)

def _fix_caps_token(tok: str) -> str:
    """
    Try all 25 Caesar shifts for a single ALL-CAPS token and keep the best
    candidate only if:
      - it improves the English-likeness by a meaningful margin, AND
      - it exceeds a minimum plausibility threshold.
    This prevents mangling acronyms like GDPR/ISO/HTML.
    """
    base = tok
    base_score = _english_token_score(base)
    best, best_score = base, base_score

    for k in range(1, 26):
        cand = _caesar_shift_token(base, k)
        sc = _english_token_score(cand)
        if sc > best_score:
            best, best_score = cand, sc

    if _zipf:
        # With wordfreq: gibberish ~0, common words ~3.5+. Require clear gain.
        improved_enough = (best_score - base_score) >= 1.0
        absolutely_plausible = best_score >= 3.3
    else:
        # Heuristic scale 0..2
        improved_enough = (best_score - base_score) >= 0.75
        absolutely_plausible = best_score >= 1.5

    return best if (improved_enough and absolutely_plausible) else base

def _fix_caesar_per_token(text: str) -> str:
    """
    Decode Caesar only for suspicious ALL-CAPS tokens (≥4 letters), token-by-token.
    Leaves mixed/lowercase text alone.
    """
    return _CAPS_TOKEN_RE.sub(lambda m: _fix_caps_token(m.group(0)), text)

# --- Public: extraction normalization ----------------------------------------

def normalize_extracted_text(
    raw: str,
    *,
    caesar_mode: str = "off",  # "off" | "safe" | "aggressive"
) -> str:
    """
    Normalize text from OCR/PDF/HTML extractors in a multilingual-safe way.

    Always:
      - Strip extractor artefacts (glyph<...>, PUA, zero-width, soft hyphen, BOM, VS).

    Optionally (when caesar_mode != "off"):
      - Attempt token-level Caesar fix on ALL-CAPS words if the text looks like it may
        contain Caesar-shifted tokens. “safe” and “aggressive” currently behave the same
        as we enforce safety per token via thresholds.
    """
    if not raw:
        return raw

    s = _strip_extraction_artifacts(raw)

    if caesar_mode != "off" and (CAPS_WORD_RE.search(s) or s.isupper()):
        s = _fix_caesar_per_token(s)

    return s

# --- Main cleaning pipeline (tests rely on this API) -------------------------

def _translate_basic(s: str) -> str:
    """Map PUA bullets to '•' and apply general punctuation/spacing translations."""
    if any(ch in s for ch in PUA_BULLETS):
        for ch in PUA_BULLETS:
            s = s.replace(ch, "•")
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
    normalize_extracted: bool = False,
    caesar_mode: str = "off",
) -> str:
    """
    General-purpose cleaner for strings:
      - Optional extraction normalization (strip artefacts; optional Caesar)
      - Unicode normalization and translation mapping
      - Remove residual PUA and control chars
      - Normalize list heads and drop ToC lines
      - Whitespace collapsing with Markdown-table preservation

    NOTE: Set `normalize_extracted=True` to remove extractor junk like `glyph<...>` early.
    """
    if not s:
        return s

    # 0) Optional pre-normalization for extracted text (multilingual-safe)
    if normalize_extracted:
        s = normalize_extracted_text(s, caesar_mode=caesar_mode)

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

    # 4) Remove remaining control characters (keeps \t \n \r)
    s = RE_CTRL.sub("", s)

    # 5) Collapse whitespace (preserving Markdown tables if requested)
    if collapse_ws:
        if preserve_markdown_tables:
            new_lines: List[str] = []
            for ln in s.splitlines():
                is_table = ln.lstrip().startswith("|") and ("|" in ln.lstrip()[1:])
                if is_table:
                    # Keep table spacing; trim only trailing spaces
                    new_lines.append(ln.rstrip())
                else:
                    ln = re.sub(r"[ \t]+", " ", ln)
                    new_lines.append(ln.strip())
            s = "\n".join(new_lines)
        else:
            s = re.sub(r"[ \t]+", " ", s)
            s = re.sub(r" ?\n ?", "\n", s)
            s = s.strip()

    return s

def clean_lines(lines: Iterable[str], **kwargs) -> List[str]:
    """Clean a list of lines by applying `clean_text` to each."""
    return [clean_text(x, **kwargs) for x in lines]

# --- Helpers for chunk cleaning ---------------------------------------------

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
    **kwargs,
):
    """
    Clean the `text` field of a list of chunks.
    Works with dict-based chunks and objects with a `text` attribute.

    Extra `**kwargs` are forwarded to `clean_text`
    (e.g., `normalize_extracted=True`, `caesar_mode="off"`).
    """
    if not in_place:
        cleaned = []

    for c in chunks:
        t = _get_text_field(c, text_key) or ""
        t2 = clean_text(
            t,
            bullet=bullet,
            preserve_markdown_tables=preserve_markdown_tables,
            **kwargs,
        )

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

# --- CLI (unchanged) --------------------------------------------------------

def main(argv: List[str] | None = None) -> None:
    """Usage:
        echo "Text \uf0b7 demo" | textnormx
        textnormx < infile.txt > outfile.txt
    """
    data = sys.stdin.read()
    sys.stdout.write(clean_text(data))
