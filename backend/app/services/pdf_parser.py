import json
import fitz

from app.services.storage import MetadataStore
from app.services.filesystem import FilesystemManager


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

    def extract_toc(self, doc: fitz.Document) -> list:
        raw_toc = doc.get_toc()
        if not raw_toc:
            return []
        return [{"level": entry[0], "title": entry[1], "page": entry[2]} for entry in raw_toc]

    async def ai_toc_fallback(self, doc: fitz.Document) -> list:
        if not self.ai_provider:
            return [{"level": 1, "title": "Full Document", "page": 1}]

        first_pages_text = ""
        for i in range(min(5, len(doc))):
            first_pages_text += f"\n--- Page {i + 1} ---\n"
            first_pages_text += doc[i].get_text("text")

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
                "content": f"Identify chapters from these first pages:\n{first_pages_text[:8000]}",
            },
        ]

        try:
            response = await self.ai_provider.chat(messages, model="deepseek-chat", json_mode=True)
            if isinstance(response, str):
                parsed = json.loads(response)
                chapters = parsed.get("chapters", [])
                return [{"level": 1, "title": c["title"], "page": c.get("page", 1)} for c in chapters]
        except Exception as e:
            print(f"AI TOC fallback failed: {e}")

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
            except Exception:
                pass

        if not saved_paths:
            try:
                drawings = page.get_drawings()
                if len(drawings) > 10:
                    mat = fitz.Matrix(2, 2)
                    pix = page.get_pixmap(matrix=mat)
                    img_path = self.filesystem.image_path(textbook_id, page_num + 1, 0)
                    pix.save(str(img_path))
                    saved_paths.append(str(img_path))
            except Exception:
                pass

        return saved_paths

    def split_into_chapters(self, doc: fitz.Document, toc_entries: list) -> list:
        total_pages = len(doc)
        chapters = []

        top_level = [e for e in toc_entries if e["level"] == 1]

        if not top_level:
            text = ""
            for i in range(total_pages):
                text += doc[i].get_text("text")
            chapters.append(ParsedChapter("1", "Full Document", 1, total_pages, text))
            return chapters

        for i, entry in enumerate(top_level):
            page_start = entry["page"]
            page_end = top_level[i + 1]["page"] - 1 if i + 1 < len(top_level) else total_pages
            chapter_num = str(i + 1)
            title = entry["title"]

            text = ""
            for page_idx in range(page_start - 1, min(page_end, total_pages)):
                text += doc[page_idx].get_text("text")

            chapters.append(ParsedChapter(chapter_num, title, page_start, page_end, text))

        return chapters

    async def parse_pdf(self, filepath: str, textbook_id: str, title: str) -> ParsedDocument:
        doc = fitz.open(filepath)
        total_pages = len(doc)

        toc_entries = self.extract_toc(doc)
        if not toc_entries:
            toc_entries = await self.ai_toc_fallback(doc)

        self.filesystem.setup_textbook_dirs(textbook_id)

        for page_num in range(0, total_pages, 5):
            self.extract_page_images(doc, page_num, textbook_id)

        chapters = self.split_into_chapters(doc, toc_entries)

        for chapter in chapters:
            text_path = self.filesystem.chapter_text_path(textbook_id, chapter.number)
            text_path.write_text(chapter.text, encoding="utf-8")

        for chapter in chapters:
            await self.storage.create_chapter(
                textbook_id=textbook_id,
                chapter_number=chapter.number,
                title=chapter.title,
                page_start=chapter.page_start,
                page_end=chapter.page_end,
            )

        await self.storage.mark_textbook_processed(textbook_id)
        doc.close()

        return ParsedDocument(textbook_id, title, total_pages, chapters)
