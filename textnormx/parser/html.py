# textnormx/parser/html.py
from __future__ import annotations
from typing import List
from .types import Element

__all__ = ["parse_html_elements"]

def parse_html_elements(html: str) -> List[Element]:
    """
    Parse HTML in elements Title/Text/Table.
    !!! Requiere beautifulsoup4 (extra: textnormx[html]).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ImportError(
            "parse_html_elements require beautifulsoup4. "
            "-> pip install textnormx[html]"
        ) from e

    soup = BeautifulSoup(html, "html.parser")
    body = soup.body or soup
    elements: List[Element] = []

    def _page(tag) -> int:
        for p in tag.parents:
            if hasattr(p, "attrs"):
                for k in ("data-page", "page", "page_no", "pageno"):
                    v = p.attrs.get(k)
                    if isinstance(v, (str, int)) and str(v).isdigit():
                        return int(v)
        return 1

    def _table_to_md(table):
        """ Convert table HTML to Markdown table.
        """
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])
            rows.append([c.get_text(" ", strip=True) for c in cells])
        if not rows:
            return ""
        header = rows[0]
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(["---"] * len(header)) + " |",
        ]
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        return "\n".join(lines)

    for tag in body.find_all(
        ["h1","h2","h3","h4","h5","h6","p","ul","ol","table","pre","blockquote"],
        recursive=True,
    ):
        n = tag.name
        if n.startswith("h"):
            txt = tag.get_text(" ", strip=True)
            if txt:
                elements.append(Element("Title", txt, _page(tag)))
            continue
        if n in ("ul", "ol"):
            for li in tag.find_all("li", recursive=False):
                txt = li.get_text(" ", strip=True)
                if txt:
                    elements.append(Element("Text", f"- {txt}", _page(li)))
            continue
        if n == "table":
            md = _table_to_md(tag)
            if md.strip():
                elements.append(Element("Table", md, _page(tag)))
            continue
        txt = tag.get_text(" ", strip=True)
        if txt:
            elements.append(Element("Text", txt, _page(tag)))

    return elements
