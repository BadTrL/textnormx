# pdf_to_images.py
from __future__ import annotations
import os
from pathlib import Path

import fitz  # PyMuPDF

def pdf_to_images(pdf_path: str | os.PathLike, out_dir: str | os.PathLike, dpi: int = 300) -> list[str]:
    """
    Render each PDF page to a PNG image at the given DPI.
    Returns a list of output file paths.
    """
    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    paths: list[str] = []

    # scale factor: 72dpi (PDF default) -> requested dpi
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for i in range(doc.page_count):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)     # RGB, no alpha
        out_path = out_dir / f"{pdf_path.stem}_page_{i+1:03d}.png"
        pix.save(out_path.as_posix())
        paths.append(out_path.as_posix())

    doc.close()
    return paths

if __name__ == "__main__":
    # Example usage
    pdf_file = "Implementing_the_Cloud_Security_Principles.pdf"  # <- your PDF path
    out_folder = "out_images"
    images = pdf_to_images(pdf_file, out_folder, dpi=300)
    print(f"Saved {len(images)} images:")
    for p in images[:5]:
        print(" -", p)
