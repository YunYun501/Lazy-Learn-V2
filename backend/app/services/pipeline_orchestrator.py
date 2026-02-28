from __future__ import annotations

from typing import Any, Optional

from app.models.pipeline_models import ExtractionStatus, PipelineStatus
from app.services.storage import MetadataStore


class PipelineOrchestrator:
    def __init__(
        self,
        store: MetadataStore,
        toc_service: Optional[Any] = None,
        relevance_service: Optional[Any] = None,
        extraction_service: Optional[Any] = None,
        description_service: Optional[Any] = None,
    ) -> None:
        self.store = store
        self.toc_service = toc_service
        self.relevance_service = relevance_service
        self.extraction_service = extraction_service
        self.description_service = description_service

    async def start_import(self, textbook_id: str, course_id: Optional[str], file_path: str) -> dict:
        try:
            title = file_path.split("/")[-1].replace("_", " ").replace(".pdf", "")
            await self.store.create_textbook(
                title=title,
                filepath=file_path,
                course=None,
                library_type="course",
                textbook_id=textbook_id,
            )
            if course_id:
                await self.store.assign_textbook_to_course(textbook_id, course_id)
            await self.store.update_textbook_pipeline_status(textbook_id, PipelineStatus.uploaded.value)
            return {"textbook_id": textbook_id, "pipeline_status": PipelineStatus.uploaded.value}
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def run_toc_phase(self, textbook_id: str) -> dict:
        try:
            textbook = await self.store.get_textbook(textbook_id)
            if not textbook:
                raise ValueError("Textbook not found")

            toc_payload = {"chapters": []}
            if self.toc_service is not None:
                toc_payload = await self.toc_service.extract_toc(textbook_id)

            chapters_created: list[dict] = []
            for chapter in toc_payload.get("chapters", []):
                chapter_id = await self.store.create_chapter(
                    textbook_id=textbook_id,
                    chapter_number=chapter.get("chapter_number", ""),
                    title=chapter.get("title", ""),
                    page_start=chapter.get("page_start", 0),
                    page_end=chapter.get("page_end", 0),
                )
                chapters_created.append(
                    {
                        "id": chapter_id,
                        "title": chapter.get("title", ""),
                        "chapter_number": chapter.get("chapter_number", ""),
                    }
                )

                for section in chapter.get("sections", []):
                    await self.store.create_section(
                        {
                            "chapter_id": chapter_id,
                            "section_number": section.get("section_number"),
                            "title": section.get("title"),
                            "page_start": section.get("page_start"),
                            "page_end": section.get("page_end"),
                        }
                    )

            relevance_results: list[dict] = []
            course_id = textbook.get("course_id")
            if course_id and self.relevance_service is not None:
                raw = await self.relevance_service.match_chapters(textbook_id, course_id)
                relevance_results = [
                    r.model_dump() if hasattr(r, "model_dump") else r for r in raw
                ]

            await self.store.update_textbook_pipeline_status(textbook_id, PipelineStatus.toc_extracted.value)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.toc_extracted.value,
                "chapters": chapters_created,
                "relevance_results": relevance_results,
            }
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def submit_verification(self, textbook_id: str, selected_chapter_ids: list[str]) -> dict:
        try:
            await self.store.update_textbook_pipeline_status(
                textbook_id,
                PipelineStatus.awaiting_verification.value,
            )
            chapters = await self.store.list_chapters(textbook_id)
            selected_set = set(selected_chapter_ids)
            for chapter in chapters:
                chapter_id = chapter["id"]
                if chapter_id in selected_set:
                    await self.store.update_chapter_extraction_status(
                        chapter_id,
                        ExtractionStatus.extracting.value,
                    )
                else:
                    await self.store.update_chapter_extraction_status(
                        chapter_id,
                        ExtractionStatus.deferred.value,
                    )

            await self.store.update_textbook_pipeline_status(
                textbook_id,
                PipelineStatus.extracting.value,
            )
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.extracting.value,
            }
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def run_extraction_phase(self, textbook_id: str, chapter_ids: list[str]) -> dict:
        try:
            if self.extraction_service is not None:
                await self.extraction_service.extract(textbook_id, chapter_ids)

            for chapter_id in chapter_ids:
                await self.store.update_chapter_extraction_status(
                    chapter_id,
                    ExtractionStatus.extracted.value,
                )

            extracted = await self.store.get_chapters_by_extraction_status(
                textbook_id,
                ExtractionStatus.extracted.value,
            )
            all_chapters = await self.store.list_chapters(textbook_id)
            if all_chapters and len(extracted) == len(all_chapters):
                status = PipelineStatus.fully_extracted
            else:
                status = PipelineStatus.partially_extracted

            await self.store.update_textbook_pipeline_status(textbook_id, status.value)
            return {"textbook_id": textbook_id, "pipeline_status": status.value}
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def run_deferred_extraction(self, textbook_id: str, chapter_ids: list[str]) -> dict:
        try:
            await self.store.update_textbook_pipeline_status(
                textbook_id,
                PipelineStatus.extracting.value,
            )
            for chapter_id in chapter_ids:
                await self.store.update_chapter_extraction_status(
                    chapter_id,
                    ExtractionStatus.extracting.value,
                )
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.extracting.value,
            }
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def run_description_phase(self, textbook_id: str, chapter_ids: list[str]) -> dict:
        try:
            if self.description_service is not None:
                await self.description_service.generate(textbook_id, chapter_ids)
            return {"textbook_id": textbook_id, "chapter_ids": chapter_ids}
        except Exception as exc:
            await self._set_error(textbook_id)
            return {
                "textbook_id": textbook_id,
                "pipeline_status": PipelineStatus.error.value,
                "error": str(exc),
            }

    async def _set_error(self, textbook_id: str) -> None:
        try:
            await self.store.update_textbook_pipeline_status(textbook_id, PipelineStatus.error.value)
        except Exception:
            return
