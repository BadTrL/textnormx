# textnormx/parser/__init__.py
from .types import Element, Chunk
from .markdown import parse_markdown_elements
from .chunk import chunk_by_title

# parseur HTML optionnel (bs4)
try:
    from .html import parse_html_elements
except Exception:  # bs4 non installé
    def parse_html_elements(*args, **kwargs):
        raise ImportError(
            "parse_html_elements nécessite beautifulsoup4. "
            "Installe l'extra: pip install textnormx[html]"
        )

__all__ = [
    "Element", "Chunk",
    "parse_markdown_elements", "parse_html_elements",
    "chunk_by_title",
]