import json
import shutil
import tempfile
from pathlib import Path

from app.models.pipeline_models import ContentType, ExtractedContent, Section
from app.services.storage import MetadataStore

try:
    from mineru.cli.common import do_parse
except ImportError:
    do_parse = None


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
        chapters = await self.store.list_chapters(textbook_id)
        chapter_map = {c["id"]: c for c in chapters if c["id"] in set(chapter_ids)}
        ordered = sorted(chapter_map.values(), key=lambda c: c["page_start"])
        results: list[ExtractedContent] = []

        for batch in self._batch_contiguous(ordered):
            results.extend(await self._extract_batch(textbook_id, batch, pdf_path))

        return results

    async def extract(self, textbook_id: str, chapter_ids: list[str]) -> list[ExtractedContent]:
        """Adapter for PipelineOrchestrator — looks up PDF path from store."""
        textbook = await self.store.get_textbook(textbook_id)
        if not textbook:
            raise ValueError("Textbook not found")
        return await self.extract_chapters(textbook_id, chapter_ids, textbook["filepath"])

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
        except Exception:
            for chapter in chapters:
                await self.store.update_chapter_extraction_status(
                    chapter["id"], "error"
                )
            return []
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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

        extracted: list[ExtractedContent] = []
        for chapter in chapters:
            chapter_id = chapter["id"]
            chapter_number = str(chapter["chapter_number"])
            entries = per_chapter_entries.get(chapter_id, [])
            try:
                extracted.extend(
                    await self._store_chapter_entries(
                        textbook_id, chapter_id, chapter_number, entries
                    )
                )
                await self.store.update_chapter_extraction_status(
                    chapter_id, "extracted"
                )
            except Exception:
                await self.store.update_chapter_extraction_status(chapter_id, "error")

        return extracted

    async def _store_chapter_entries(
        self,
        textbook_id: str,
        chapter_id: str,
        chapter_number: str,
        entries: list[dict],
    ) -> list[ExtractedContent]:
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

        for index, entry in enumerate(entries, start=1):
            content_type = self._map_content_type(entry.get("type"))
            if content_type is None:
                continue
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
        return None, entry.get("text")
