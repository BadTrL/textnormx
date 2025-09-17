# textnormx/parser/types.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Dict, Any

ElementType = Literal["Title", "Text", "Table"]
ChunkType   = Literal["Text", "Table"]

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
