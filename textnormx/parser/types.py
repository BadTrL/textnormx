# textnormx/parser/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Any
import re

ElementType = Literal["Title", "Text", "Table"]
ChunkType   = Literal["Text", "Table"]

HTML_TAG_RE = re.compile(r"</?(?:html|body|p|div|span|table|thead|tbody|tr|td|th|ul|ol|li|h[1-6])\b", re.I)
MD_CUES_RE  = re.compile(r"(^|\n)#{1,6}\s|^\s*\|.*\|\s*$", re.M)

def detect_format(s: str) -> str:
    if not s: return "plain"
    if HTML_TAG_RE.search(s): return "html"
    if MD_CUES_RE.search(s): return "md"
    return "plain"

@dataclass
class Element:
    type: ElementType
    text: str
    page: int = 1

@dataclass
class Chunk:
    text: str
    element_id: str
    type: ChunkType
    metadata: Dict[str, Any]
