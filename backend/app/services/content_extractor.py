import json
import logging
import re
import shutil
import tempfile
from pathlib import Path

from app.models.pipeline_models import ContentType, ExtractedContent, Section
from app.services.storage import MetadataStore

logger = logging.getLogger(__name__)

try:
    from mineru.cli.common import do_parse
except ImportError:
    do_parse = None

# Fallback heading detection for books without TOC sections in DB
_SECTION_HEADING_RE = re.compile(r"^(\d+\.\d+(?:\.\d+)*)\s+(.+)$")
_MAX_HEADING_LEN = 150


class ContentExtractor:
    def __init__(self, store: MetadataStore):
        self.store = store
        self.data_dir = Path("data")

    async def extract_chapters(
        self,
        textbook_id: str,
        chapter_ids: list[str],
        pdf_path: str,
    ) -> list[ExtractedContent]:
        logger.info(
            "Extracting %d chapters from %s",
            len(chapter_ids),
            pdf_path,
            extra={"textbook_id": textbook_id},
        )
        chapters = await self.store.list_chapters(textbook_id)
        chapter_map = {c["id"]: c for c in chapters if c["id"] in set(chapter_ids)}
        ordered = sorted(chapter_map.values(), key=lambda c: c["page_start"])
        results: list[ExtractedContent] = []

        for batch in self._batch_contiguous(ordered):
            results.extend(await self._extract_batch(textbook_id, batch, pdf_path))

        logger.info(
            "Extraction complete: %d content entries",
            len(results),
            extra={"textbook_id": textbook_id},
        )
        return results

    async def extract(
        self, textbook_id: str, chapter_ids: list[str]
    ) -> list[ExtractedContent]:
        """Adapter for PipelineOrchestrator — looks up PDF path from store."""
        textbook = await self.store.get_textbook(textbook_id)
        if not textbook:
            raise ValueError("Textbook not found")
        return await self.extract_chapters(
            textbook_id, chapter_ids, textbook["filepath"]
        )

    async def extract_sections(
        self,
        textbook_id: str,
        chapter_id: str,
        toc_entries: list,
    ) -> list[Section]:
        level_two_entries = [e for e in toc_entries if e.get("level") == 2]
        if not level_two_entries:
            return []

        sections: list[Section] = []
        for section_number, entry in enumerate(level_two_entries, start=1):
            page_start = entry.get("page")
            page_end = self._find_section_end(toc_entries, entry)
            section_data = {
                "chapter_id": chapter_id,
                "section_number": section_number,
                "title": entry.get("title"),
                "page_start": page_start,
                "page_end": page_end,
            }
            section_id = await self.store.create_section(section_data)
            sections.append(
                Section(
                    id=section_id,
                    chapter_id=chapter_id,
                    section_number=section_number,
                    title=entry.get("title"),
                    page_start=page_start,
                    page_end=page_end,
                )
            )

        return sections

    # ------------------------------------------------------------------
    # Text merging — group MinerU fragments into coherent sections
    # ------------------------------------------------------------------

    def _find_section_for_page(
        self, page: int | None, sections: list[dict]
    ) -> dict | None:
        """Find the most specific (deepest-level) section for a given page.

        Sections may overlap (a parent spans all child pages).  We pick
        the deepest-level section whose page range contains ``page``.
        """
        if page is None:
            return None
        best: dict | None = None
        for sec in sections:
            start = sec.get("page_start") or 0
            # Some sections have bad page_end (end < start) — treat as single page
            end = sec.get("page_end") or start
            if end < start:
                end = start
            if start <= page <= end:
                if best is None or sec.get("level", 2) > best.get("level", 2):
                    best = sec
        return best

    async def _merge_text_by_section(
        self, entries: list[dict], chapter_id: str
    ) -> list[dict]:
        """Merge fragmented text entries into section-level blocks.

        **Primary strategy (format-agnostic)**: Use the TOC-derived sections
        from the DB.  Each entry is assigned to a section by its page number.
        All text entries in the same section are concatenated.

        **Fallback**: If no sections exist in the DB, fall back to regex-based
        heading detection (``1.2.3 Title`` pattern).

        Non-text entries (figure, table, equation) pass through unchanged.
        """
        sections = await self.store.get_all_sections_for_chapter(chapter_id)
        if not sections:
            return self._merge_text_by_heading_regex(entries)

        # --- Page-based merge using TOC sections ---
        merged: list[dict] = []
        current_section: dict | None = None
        current_texts: list[str] = []
        current_page: int | None = None

        def _flush() -> None:
            nonlocal current_section, current_texts, current_page
            if not current_texts:
                current_section = None
                current_page = None
                return
            title = current_section["title"] if current_section else None
            heading = f"## {title}" if title else None
            parts = [heading] if heading else []
            parts.extend(current_texts)
            merged.append(
                {
                    "type": "text",
                    "text": "\n\n".join(parts),
                    "page_number": current_page,
                    "_section_title": title,
                }
            )
            current_section = None
            current_texts = []
            current_page = None

        for entry in entries:
            if entry.get("type") != "text":
                _flush()
                merged.append(entry)
                continue

            text = (entry.get("text") or "").strip()
            if not text:
                continue

            page = entry.get("page_number")
            sec = self._find_section_for_page(page, sections)

            # Section changed — flush previous block
            sec_id = sec["id"] if sec else None
            cur_id = current_section["id"] if current_section else None
            if sec_id != cur_id:
                _flush()
                current_section = sec
                current_page = page

            # Skip the heading text itself — it's now the section title
            sec_title = (sec["title"] if sec else "").strip().rstrip(".")
            text_stripped = text.strip().rstrip(".")
            if sec_title and text_stripped.lower() == sec_title.lower():
                if current_page is None:
                    current_page = page
                continue

            current_texts.append(text)
            if current_page is None:
                current_page = page

        _flush()
        return merged

    def _merge_text_by_heading_regex(self, entries: list[dict]) -> list[dict]:
        """Fallback: merge text by detecting numbered headings via regex.

        Used only when no TOC sections exist in the DB for this chapter.
        """
        merged: list[dict] = []
        section_title: str | None = None
        section_texts: list[str] = []
        section_page: int | None = None

        def _flush() -> None:
            nonlocal section_title, section_texts, section_page
            if not section_texts and section_title is None:
                return
            parts: list[str] = []
            if section_title:
                parts.append(f"## {section_title}")
            parts.extend(section_texts)
            merged.append(
                {
                    "type": "text",
                    "text": "\n\n".join(parts),
                    "page_number": section_page,
                    "_section_title": section_title,
                }
            )
            section_title = None
            section_texts = []
            section_page = None

        for entry in entries:
            if entry.get("type") != "text":
                _flush()
                merged.append(entry)
                continue

            text = (entry.get("text") or "").strip()
            if not text:
                continue

            if _SECTION_HEADING_RE.match(text) and len(text) < _MAX_HEADING_LEN:
                _flush()
                section_title = text
                section_page = entry.get("page_number")
            else:
                section_texts.append(text)
                if section_page is None:
                    section_page = entry.get("page_number")

        _flush()
        return merged

    # ------------------------------------------------------------------
    # Batch extraction
    # ------------------------------------------------------------------

    def _batch_contiguous(self, chapters: list[dict]) -> list[list[dict]]:
        batches: list[list[dict]] = []
        current: list[dict] = []
        for chapter in chapters:
            if not current:
                current = [chapter]
                continue
            previous = current[-1]
            if previous["page_end"] + 1 == chapter["page_start"]:
                current.append(chapter)
            else:
                batches.append(current)
                current = [chapter]
        if current:
            batches.append(current)
        return batches

    def _find_section_end(self, toc_entries: list, entry: dict) -> int:
        start_index = toc_entries.index(entry)
        for next_entry in toc_entries[start_index + 1 :]:
            if next_entry.get("level") in {1, 2}:
                next_page = next_entry.get("page")
                if next_page is not None:
                    return max(int(next_page) - 1, int(entry.get("page", next_page)))
        return int(entry.get("page", 1))

    async def _extract_batch(
        self,
        textbook_id: str,
        chapters: list[dict],
        pdf_path: str,
    ) -> list[ExtractedContent]:
        if do_parse is None:
            raise RuntimeError("MinerU is not available")

        start_page = min(c["page_start"] for c in chapters)
        end_page = max(c["page_end"] for c in chapters)
        start_page_id = start_page - 1
        end_page_id = end_page - 1

        pdf_bytes = b""
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            pdf_bytes = pdf_file.read_bytes()

        temp_dir = tempfile.mkdtemp()
        try:
            do_parse(
                output_dir=temp_dir,
                pdf_file_names=["document"],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=["en"],
                backend="pipeline",
                parse_method="auto",
                formula_enable=True,
                table_enable=True,
                f_dump_md=True,
                f_dump_content_list=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                start_page_id=start_page_id,
                end_page_id=end_page_id,
            )
            content_path = (
                Path(temp_dir) / "document" / "auto" / "document_content_list.json"
            )
            if not content_path.exists():
                raise RuntimeError("MinerU content list missing")
            content_entries = json.loads(content_path.read_text(encoding="utf-8"))

            # --- Assign entries to chapters while temp_dir still exists ---
            per_chapter_entries: dict[str, list[dict]] = {c["id"]: [] for c in chapters}
            for entry in content_entries:
                entry_type = entry.get("type")
                if entry_type == "discarded":
                    continue
                page_idx = entry.get("page_idx")
                if page_idx is None:
                    continue
                page_number = start_page_id + int(page_idx) + 1
                for chapter in chapters:
                    if chapter["page_start"] <= page_number <= chapter["page_end"]:
                        per_chapter_entries[chapter["id"]].append(
                            {**entry, "page_number": page_number}
                        )
                        break

            # --- Store entries (copies images) while temp_dir still exists ---
            extracted: list[ExtractedContent] = []
            for chapter in chapters:
                chapter_id = chapter["id"]
                chapter_number = str(chapter["chapter_number"])
                entries = per_chapter_entries.get(chapter_id, [])
                try:
                    logger.info(
                        "Chapter extraction started",
                        extra={"textbook_id": textbook_id, "chapter_id": chapter_id},
                    )
                    extracted.extend(
                        await self._store_chapter_entries(
                            textbook_id, chapter_id, chapter_number, entries, temp_dir
                        )
                    )
                    await self.store.update_chapter_extraction_status(
                        chapter_id, "extracted"
                    )
                    logger.info(
                        "Chapter extraction completed",
                        extra={
                            "textbook_id": textbook_id,
                            "chapter_id": chapter_id,
                            "entry_count": len(entries),
                        },
                    )
                except Exception:
                    logger.error(
                        "Chapter extraction failed",
                        extra={"textbook_id": textbook_id, "chapter_id": chapter_id},
                        exc_info=True,
                    )
                    await self.store.update_chapter_extraction_status(
                        chapter_id, "error"
                    )

            return extracted
        except Exception:
            logger.error(
                "Batch extraction failed",
                extra={"textbook_id": textbook_id},
                exc_info=True,
            )
            for chapter in chapters:
                await self.store.update_chapter_extraction_status(
                    chapter["id"], "error"
                )
            return []
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    async def _store_chapter_entries(
        self,
        textbook_id: str,
        chapter_id: str,
        chapter_number: str,
        entries: list[dict],
        temp_dir: str,
    ) -> list[ExtractedContent]:
        # Merge fragmented text into section-level blocks
        entries = await self._merge_text_by_section(entries, chapter_id)

        stored: list[ExtractedContent] = []
        content_dir = (
            self.data_dir
            / "textbooks"
            / textbook_id
            / "chapters"
            / chapter_number
            / "content"
        )
        content_dir.mkdir(parents=True, exist_ok=True)
        images_dir = content_dir / "images"

        for index, entry in enumerate(entries, start=1):
            content_type = self._map_content_type(entry.get("type"))
            if content_type is None:
                continue

            # Copy image files to permanent storage before temp_dir is cleaned up
            if content_type == ContentType.figure:
                entry = self._persist_image(entry, images_dir, temp_dir, index)

            title, content = self._entry_title_and_content(entry, content_type)
            file_path = content_dir / f"{content_type.value}_{index}.md"
            file_path.write_text(content or "", encoding="utf-8")

            content_data = {
                "chapter_id": chapter_id,
                "content_type": content_type.value,
                "title": title,
                "content": content,
                "file_path": str(file_path),
                "page_number": entry.get("page_number"),
                "order_index": index,
            }
            content_id = await self.store.create_extracted_content(content_data)
            stored.append(
                ExtractedContent(
                    id=content_id,
                    chapter_id=chapter_id,
                    content_type=content_type,
                    title=title,
                    content=content,
                    file_path=str(file_path),
                    page_number=entry.get("page_number"),
                    order_index=index,
                )
            )

        return stored

    def _persist_image(
        self, entry: dict, images_dir: Path, temp_dir: str, index: int
    ) -> dict:
        """Copy a figure image from MinerU's temp output to permanent storage.

        Returns a new entry dict with ``img_path`` pointing to the permanent copy.
        """
        img_path = entry.get("img_path") or ""
        if not img_path:
            return entry

        src = Path(temp_dir) / img_path
        if not src.exists():
            src = Path(img_path)
        if not src.exists():
            return entry

        images_dir.mkdir(parents=True, exist_ok=True)
        dest = images_dir / f"figure_{index}{src.suffix}"
        shutil.copy2(str(src), str(dest))

        return {**entry, "img_path": str(dest)}

    def _map_content_type(self, mineru_type: str | None) -> ContentType | None:
        if mineru_type == "text":
            return ContentType.text
        if mineru_type == "table":
            return ContentType.table
        if mineru_type == "equation":
            return ContentType.equation
        if mineru_type == "image":
            return ContentType.figure
        return None

    def _entry_title_and_content(
        self, entry: dict, content_type: ContentType
    ) -> tuple[str | None, str | None]:
        if content_type == ContentType.figure:
            caption = entry.get("image_caption") or []
            title = caption[0] if caption else None
            img_path = entry.get("img_path") or ""
            parts = []
            if title:
                parts.append(f"# {title}")
            if img_path:
                parts.append(f"![{title or 'figure'}]({img_path})")
            footnotes = entry.get("image_footnote") or []
            parts.extend(footnotes)
            return title, "\n\n".join(parts)
        if content_type == ContentType.equation:
            return None, entry.get("text")
        # For merged text entries, use the section title
        section_title = entry.get("_section_title")
        return section_title, entry.get("text")
