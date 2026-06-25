from pathlib import Path
import sys

from pypdf import PdfReader


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: extract_pdf_text.py INPUT_PDF OUTPUT_TXT")
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(src))
    chunks = []
    for index, page in enumerate(reader.pages, start=1):
        chunks.append(f"\n\n--- PAGE {index} ---\n")
        chunks.append(page.extract_text() or "")

    dst.write_text("".join(chunks), encoding="utf-8")
    print(f"pages={len(reader.pages)} output={dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
