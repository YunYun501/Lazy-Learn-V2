import json
import logging
import re
from pathlib import Path

import fitz

from app.services.storage import MetadataStore
from app.services.filesystem import FilesystemManager

try:
    from app.services.mineru_parser import MinerUExtractor
except ImportError:
    MinerUExtractor = None

logger = logging.getLogger(__name__)


_SECTION_NUMBER_RE = re.compile(r'^\d+\.\d+')

_META_TITLES = {
    'contents', 'preface', 'index', 'bibliography',
    'list of contributors', 'foreword', 'acknowledgments',
    'acknowledgements', 'about the authors', 'about the author',
    'about the editor', 'about the editors', 'appendix',
    'glossary', 'table of contents',
}


def _fixup_zero_pages(toc_entries: list[dict]) -> list[dict]:
    """Repair entries with page=0 by inferring from the next valid entry."""
    fixed = [dict(e) for e in toc_entries]
    for i, entry in enumerate(fixed):
        if entry.get('page', 0) > 0:
            continue
        # Look forward for the first entry with a valid page
        for j in range(i + 1, len(fixed)):
            if fixed[j].get('page', 0) > 0:
                entry['page'] = fixed[j]['page']
                break
    return fixed


def _filter_meta(entries: list[dict]) -> list[dict]:
    """Remove meta entries (Contents, Preface, Index, etc.) from chapter list."""
    filtered = [
        e for e in entries
        if e.get('title', '').strip().lower() not in _META_TITLES
    ]
    return filtered if filtered else entries


def detect_chapter_entries(toc_entries: list[dict]) -> list[dict]:
    """Detect actual chapter entries from a TOC that may have mixed levels.

    Handles three structures:
      1. Simple: all chapters at level 1 (returns level-1 entries).
      2. Part\u2192Chapter: Parts at level 1, chapters at level 2.
      3. Mixed: some chapters directly at level 1, others nested under
         Part headings at level 2.

    The algorithm identifies level-1 \"containers\" (entries whose page range
    spans level-2 children). Containers are Part headings and are excluded;
    their level-2 children plus any non-container level-1 entries form the
    chapter list.

    Page-0 entries are repaired by inferring from subsequent entries.
    Meta entries like 'Contents' and 'Preface' are always filtered out.
    """
    if not toc_entries:
        return []

    # Fix broken page=0 bookmarks before any sorting/analysis
    fixed = _fixup_zero_pages(toc_entries)

    level1 = [e for e in fixed if e.get('level') == 1]
    level2 = [e for e in fixed if e.get('level') == 2]

    # Only one level present \u2192 straightforward
    if not level2:
        return _filter_meta(sorted(level1, key=lambda e: e.get('page', 0)))
    if not level1:
        return _filter_meta(sorted(level2, key=lambda e: e.get('page', 0)))

    # If level-2 titles look like sub-sections (\"1.1 \u2026\", \"2.3 \u2026\"),
    # then level 1 = chapters, level 2 = sections \u2192 use level 1.
    section_like = sum(
        1 for e in level2
        if _SECTION_NUMBER_RE.match(e.get('title', '').strip())
    )
    if section_like > len(level2) * 0.5:
        return _filter_meta(sorted(level1, key=lambda e: e.get('page', 0)))

    # Level-2 titles look like chapters (not dotted sections).
    # Determine which level-1 entries are containers (Parts).
    level1_sorted = sorted(level1, key=lambda e: e.get('page', 0))
    container_mask: list[bool] = []

    for i, entry in enumerate(level1_sorted):
        page = entry.get('page', 0)
        next_page = (
            level1_sorted[i + 1].get('page', float('inf'))
            if i + 1 < len(level1_sorted)
            else float('inf')
        )
        has_children = any(
            page <= child.get('page', 0) < next_page
            for child in level2
        )
        container_mask.append(has_children)

    container_count = sum(container_mask)

    if container_count == 0:
        # No containers \u2013 level 1 = chapters
        return _filter_meta(level1_sorted)
    elif container_count == len(level1_sorted):
        # ALL level-1 entries are containers \u2192 level 2 = chapters
        return _filter_meta(sorted(level2, key=lambda e: e.get('page', 0)))
    else:
        # Mixed: non-container level-1 entries + all level-2 entries
        chapters: list[dict] = []
        for i, entry in enumerate(level1_sorted):
            if not container_mask[i]:
                chapters.append(entry)
        chapters.extend(level2)
        chapters.sort(key=lambda e: e.get('page', 0))
        return _filter_meta(chapters)

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

    async def ai_toc_from_text(self, pages_text: str) -> list:
        """Use AI to extract a comprehensive TOC from raw page text.

        Works with text from any source (embedded PDF text or OCR output).
        Returns list of dicts: [{"level": int, "title": str, "page": int}, ...].
        """
        if not self.ai_provider:
            return [{"level": 1, "title": "Full Document", "page": 1}]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are analyzing a textbook. Based on the provided page text, "
                    "identify the COMPLETE chapter structure including parts, chapters, "
                    "sections, and subsections. Be thorough — capture every structural "
                    "heading you find.\n\n"
                    "Return JSON with this exact format:\n"
                    '{"toc_entries": [\n'
                    '  {"level": 1, "title": "Part I: Fundamentals", "page": 1},\n'
                    '  {"level": 2, "title": "1 Introduction", "page": 1},\n'
                    '  {"level": 3, "title": "1.1 Background", "page": 3},\n'
                    '  ...\n'
                    ']}\n\n'
                    "Level guidelines:\n"
                    "- level 1: Parts or top-level chapters (if no parts)\n"
                    "- level 2: Chapters (under parts) or sections (if no parts)\n"
                    "- level 3: Sections or subsections\n"
                    "\nPage numbers MUST match what appears in the text. "
                    "Do NOT invent entries — only include headings you can see in the text."
                ),
            },
            {
                "role": "user",
                "content": f"Identify the complete table of contents from these pages:\n{pages_text[:48000]}",
            },
        ]

        try:
            response = await self.ai_provider.chat(messages, model="deepseek-chat", json_mode=True)
            if isinstance(response, str):
                parsed = json.loads(response)
                # Support both response formats
                entries = parsed.get("toc_entries") or parsed.get("chapters", [])
                result = []
                for entry in entries:
                    result.append({
                        "level": entry.get("level", 1),
                        "title": entry.get("title", entry.get("number", "")),
                        "page": entry.get("page", 1),
                    })
                return result if result else [{"level": 1, "title": "Full Document", "page": 1}]
        except Exception as e:
            logger.warning(f"AI TOC extraction failed: {e}")

        return [{"level": 1, "title": "Full Document", "page": 1}]

    async def ai_toc_fallback(self, doc: fitz.Document) -> list:
        """Extract TOC from embedded PDF text using AI (fallback when no bookmarks)."""
        first_pages_text = ""
        for i in range(min(30, len(doc))):
            first_pages_text += f"\n--- Page {i + 1} ---\n"
            first_pages_text += str(doc[i].get_text("text"))
        return await self.ai_toc_from_text(first_pages_text)

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

        chapter_entries = detect_chapter_entries(toc_entries)

        if not chapter_entries:
            text = ""
            for i in range(total_pages):
                if mineru_pages and (i + 1) in mineru_pages:
                    text += mineru_pages[i + 1]
                else:
                    text += str(doc[i].get_text("text"))
            chapters.append(ParsedChapter("1", "Full Document", 1, total_pages, text))
            return chapters

        for i, entry in enumerate(chapter_entries):
            page_start = entry["page"]
            page_end = chapter_entries[i + 1]["page"] - 1 if i + 1 < len(chapter_entries) else total_pages
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
