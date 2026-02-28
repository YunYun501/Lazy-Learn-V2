"""Re-extract scanned PDF chapters using MinerU.

Run: python backend/scripts/reextract_scanned.py
Takes ~1-2 hours for 860-page scanned PDF on RTX 3060.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz
from app.services.mineru_parser import MinerUExtractor

TEXTBOOK_ID = "07685261-7ffc-499a-bba7-23271ee457fb"
PDF_PATH = Path(__file__).resolve().parents[1] / "data" / "textbooks" / TEXTBOOK_ID / "original.pdf"
CHAPTERS_DIR = Path(__file__).resolve().parents[1] / "data" / "textbooks" / TEXTBOOK_ID / "chapters"


def main():
    print(f"PDF: {PDF_PATH}")
    print(f"PDF exists: {PDF_PATH.exists()}")
    print(f"PDF size: {PDF_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    # Get TOC from PyMuPDF
    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    print(f"Total pages: {total_pages}")

    raw_toc = doc.get_toc()
    toc_entries = [{"level": e[0], "title": e[1], "page": e[2]} for e in raw_toc]
    top_level = [e for e in toc_entries if e["level"] == 1]
    print(f"TOC entries: {len(toc_entries)}, top-level chapters: {len(top_level)}")
    doc.close()

    # Run MinerU extraction
    print(f"\nStarting MinerU extraction on {total_pages} pages...")
    print("This will take 1-2 hours for an 860-page scanned PDF.")
    start = time.time()

    extractor = MinerUExtractor()
    if not extractor.is_available():
        print("ERROR: MinerU not available!")
        sys.exit(1)

    pdf_bytes = PDF_PATH.read_bytes()
    mineru_pages = extractor.extract_text_by_pages(pdf_bytes, output_dir=str(CHAPTERS_DIR.parent))

    elapsed = time.time() - start
    print(f"\nMinerU extraction completed in {elapsed / 60:.1f} minutes")
    print(f"Extracted text for {len(mineru_pages)} pages")
    total_chars = sum(len(t) for t in mineru_pages.values())
    print(f"Total characters extracted: {total_chars:,}")

    if not mineru_pages:
        print("ERROR: No text extracted!")
        sys.exit(1)

    # Split into chapters using TOC page ranges
    for i, entry in enumerate(top_level):
        page_start = entry["page"]
        page_end = top_level[i + 1]["page"] - 1 if i + 1 < len(top_level) else total_pages
        chapter_num = str(i + 1)

        text = ""
        for page_idx in range(page_start - 1, min(page_end, total_pages)):
            if (page_idx + 1) in mineru_pages:
                text += mineru_pages[page_idx + 1]

        chapter_path = CHAPTERS_DIR / f"{chapter_num}.txt"
        chapter_path.write_text(text, encoding="utf-8")
        print(f'  Ch.{chapter_num} "{entry["title"]}": {len(text):,} chars')

    print("\nDone! All chapters re-extracted with MinerU.")


if __name__ == "__main__":
    main()
