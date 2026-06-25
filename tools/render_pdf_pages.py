from pathlib import Path
import sys

import fitz


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_pdf_pages.py INPUT_PDF OUTPUT_DIR")
        return 2
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(src)
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        pix.save(out / f"page_{page_index + 1:02d}.png")
    print(f"pages={len(doc)} output={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
