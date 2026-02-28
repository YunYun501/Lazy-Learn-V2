import json
import logging
from pathlib import Path

import fitz

from app.services.storage import MetadataStore
from app.services.filesystem import FilesystemManager

try:
    from app.services.mineru_parser import MinerUExtractor
except ImportError:
    MinerUExtractor = None

logger = logging.getLogger(__name__)


class ParsedChapter:
    def __init__(self, number: str, title: str, page_start: int, page_end: int, text: str):
        self.number = number
        self.title = title
        self.page_start = page_start
        self.page_end = page_end
        self.text = text


class ParsedDocument:
    def __init__(self, textbook_id: str, title: str, total_pages: int, chapters: list):
        self.textbook_id = textbook_id
        self.title = title
        self.total_pages = total_pages
        self.chapters = chapters


class PDFParser:
    def __init__(self, storage: MetadataStore, filesystem: FilesystemManager, ai_provider=None):
        self.storage = storage
        self.filesystem = filesystem
        self.ai_provider = ai_provider
        self.mineru_extractor = None

        if MinerUExtractor is None:
            logger.info("MinerU module not available; falling back to PyMuPDF text extraction.")
        else:
            self.mineru_extractor = MinerUExtractor()

    def is_flattened(self, doc: fitz.Document) -> bool:
        """Check if PDF is scanned/image-only (no embedded text layer)."""
        sample_pages = min(5, len(doc))
        for i in range(sample_pages):
            text = doc[i].get_text("text").strip()
            if len(text) > 100:
                return False
        return True

    def extract_toc(self, doc: fitz.Document) -> list:
        raw_toc = doc.get_toc()
        if not raw_toc:
            return []
        return [{"level": entry[0], "title": entry[1], "page": entry[2]} for entry in raw_toc]

    async def ai_toc_fallback(self, doc: fitz.Document) -> list:
        if not self.ai_provider:
            return [{"level": 1, "title": "Full Document", "page": 1}]

        first_pages_text = ""
        for i in range(min(30, len(doc))):
            first_pages_text += f"\n--- Page {i + 1} ---\n"
            first_pages_text += str(doc[i].get_text("text"))

        messages = [
            {
                "role": "system",
                "content": (
                    "You are analyzing a textbook PDF. Based on the first few pages, "
                    "identify the chapter structure. Return JSON: "
                    '{"chapters": [{"number": "1", "title": "Chapter Title", "page": 1}]}'
                ),
            },
            {
                "role": "user",
                "content": f"Identify chapters from these first pages:\n{first_pages_text[:48000]}",
            },
        ]

        try:
            response = await self.ai_provider.chat(messages, model="deepseek-chat", json_mode=True)
            if isinstance(response, str):
                parsed = json.loads(response)
                chapters = parsed.get("chapters", [])
                return [{"level": 1, "title": c["title"], "page": c.get("page", 1)} for c in chapters]
        except Exception as e:
            logger.warning(f"AI TOC fallback failed: {e}")

        return [{"level": 1, "title": "Full Document", "page": 1}]

    def extract_page_images(self, doc: fitz.Document, page_num: int, textbook_id: str) -> list:
        saved_paths = []
        page = doc[page_num]

        image_list = page.get_images(full=True)
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                if len(image_bytes) > 2048:
                    img_path = self.filesystem.image_path(textbook_id, page_num + 1, img_index)
                    img_path.write_bytes(image_bytes)
                    saved_paths.append(str(img_path))
            except Exception as e:
                logger.warning(f"Image extraction failed for xref {xref}: {e}")

        if not saved_paths:
            try:
                drawings = page.get_drawings()
                if len(drawings) > 10:
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat)
                    img_path = self.filesystem.image_path(textbook_id, page_num + 1, 0)
                    pix.save(str(img_path))
                    saved_paths.append(str(img_path))
            except Exception as e:
                logger.warning(f"Fallback image extraction failed: {e}")

        return saved_paths

    def split_into_chapters(
        self,
        doc: fitz.Document,
        toc_entries: list,
        mineru_pages: dict[int, str] | None = None,
    ) -> list:
        total_pages = len(doc)
        chapters = []

        top_level = [e for e in toc_entries if e["level"] == 1]

        if not top_level:
            text = ""
            for i in range(total_pages):
                if mineru_pages and (i + 1) in mineru_pages:
                    text += mineru_pages[i + 1]
                else:
                    text += str(doc[i].get_text("text"))
            chapters.append(ParsedChapter("1", "Full Document", 1, total_pages, text))
            return chapters

        for i, entry in enumerate(top_level):
            page_start = entry["page"]
            page_end = top_level[i + 1]["page"] - 1 if i + 1 < len(top_level) else total_pages
            chapter_num = str(i + 1)
            title = entry["title"]

            text = ""
            for page_idx in range(page_start - 1, min(page_end, total_pages)):
                if mineru_pages and (page_idx + 1) in mineru_pages:
                    text += mineru_pages[page_idx + 1]
                else:
                    text += str(doc[page_idx].get_text("text"))

            chapters.append(ParsedChapter(chapter_num, title, page_start, page_end, text))

        return chapters

    async def parse_pdf(self, filepath: str, textbook_id: str, title: str, on_progress=None) -> ParsedDocument:
        def progress(pct: int, step: str):
            if on_progress:
                on_progress(pct, step)

        progress(20, "Opening PDF...")
        doc = fitz.open(filepath)
        total_pages = len(doc)

        progress(25, "Extracting table of contents...")
        toc_entries = self.extract_toc(doc)
        if not toc_entries:
            progress(30, "No TOC found, using AI to detect chapters...")
            toc_entries = await self.ai_toc_fallback(doc)

        progress(40, "Extracting text content...")
        mineru_pages = None
        if self.mineru_extractor and self.mineru_extractor.is_available():
            progress(40, "Running MinerU text extraction (this may take a while)...")
            pdf_bytes = Path(filepath).read_bytes()
            mineru_pages = self.mineru_extractor.extract_text_by_pages(
                pdf_bytes,
                output_dir=str(self.filesystem.data_dir),
            )

        progress(55, "Setting up directories...")
        self.filesystem.setup_textbook_dirs(textbook_id)

        progress(60, f"Extracting images from {total_pages} pages...")
        for page_num in range(0, total_pages, 5):
            self.extract_page_images(doc, page_num, textbook_id)

        progress(75, "Splitting into chapters...")
        chapters = self.split_into_chapters(doc, toc_entries, mineru_pages=mineru_pages)

        progress(85, f"Saving {len(chapters)} chapters...")
        for chapter in chapters:
            text_path = self.filesystem.chapter_text_path(textbook_id, chapter.number)
            text_path.write_text(chapter.text, encoding="utf-8")

        progress(92, "Saving metadata to database...")
        for chapter in chapters:
            await self.storage.create_chapter(
                textbook_id=textbook_id,
                chapter_number=chapter.number,
                title=chapter.title,
                page_start=chapter.page_start,
                page_end=chapter.page_end,
            )

        progress(98, "Finalizing...")
        await self.storage.mark_textbook_processed(textbook_id)
        doc.close()

        return ParsedDocument(textbook_id, title, total_pages, chapters)
