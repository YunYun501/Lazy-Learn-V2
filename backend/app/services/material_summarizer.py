"""Material Summarizer service — extract text from course materials and summarize via AI."""
import uuid
from pathlib import Path
from typing import Optional

from app.models.pipeline_models import MaterialSummary, MaterialTopic
from app.services.storage import MetadataStore

SUMMARIZE_SYSTEM_PROMPT = (
    "You are a course material summarizer. "
    "Your task is to analyze academic course materials and identify the distinct topics covered.\n\n"
    "For each distinct topic, provide:\n"
    "- title: A concise topic title\n"
    "- description: A 2-3 sentence description of what the topic covers\n"
    "- source_range: Which pages or slides cover this topic (e.g. 'pages 1-5', 'slides 3-7')\n\n"
    "Also provide a brief overall raw_summary of the entire document.\n\n"
    'Return ONLY valid JSON with this exact schema:\n'
    '{"topics": [{"title": "...", "description": "...", "source_range": "..."}], "raw_summary": "..."}'
)

MAX_CHARS_FOR_SUMMARY = 15_000


class MaterialSummarizer:
    """Extracts text from course materials (PDF/PPTX/DOCX) and summarizes via AI.

    One AI call is made per document — never per page or slide.
    """

    def __init__(
        self,
        store: MetadataStore,
        ai_router,
        document_parser=None,
    ) -> None:
        self.store = store
        self.ai_router = ai_router
        self.parser = document_parser


    def _extract_text_from_pdf(
        self, filepath: str, max_chars: int = MAX_CHARS_FOR_SUMMARY
    ) -> str:
        try:
            import fitz  # PyMuPDF  # noqa: PLC0415

            doc = fitz.open(filepath)
            text_parts: list[str] = []
            total_chars = 0
            for page_num in range(len(doc)):
                page_text = doc[page_num].get_text()
                text_parts.append(page_text)
                total_chars += len(page_text)
                if total_chars >= max_chars:
                    break
            doc.close()
            return "\n".join(text_parts)[:max_chars]
        except Exception as exc:  # noqa: BLE001
            return f"[PDF extraction error: {exc}]"

    def _extract_text_from_document(
        self, filepath: str, max_chars: int = MAX_CHARS_FOR_SUMMARY
    ) -> str:
        if self.parser is None:
            return ""
        try:
            parsed = self.parser.parse(filepath)
            text_parts: list[str] = []
            total_chars = 0
            for chapter in parsed.chapters:
                chapter_text = chapter.get("text", "")
                text_parts.append(chapter_text)
                total_chars += len(chapter_text)
                if total_chars >= max_chars:
                    break
            return "\n".join(text_parts)[:max_chars]
        except Exception as exc:  # noqa: BLE001
            return f"[Document extraction error: {exc}]"

    def _extract_text(self, filepath: str) -> str:
        ext = Path(filepath).suffix.lower()
        if ext == ".pdf":
            return self._extract_text_from_pdf(filepath)
        if ext in (".pptx", ".docx"):
            return self._extract_text_from_document(filepath)
        return ""


    async def summarize(
        self, material_id: str, file_path: str, course_id: str
    ) -> MaterialSummary:
        text = self._extract_text(file_path)

        if not text or text.startswith("["):
            return MaterialSummary(
                id=str(uuid.uuid4()),
                material_id=material_id,
                course_id=course_id,
                topics=[],
                raw_summary="Error: No extractable text found in document",
            )

        messages = [
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Summarize this course material. "
                    "For each distinct topic covered, provide:\n"
                    "- topic title\n"
                    "- description (2-3 sentences)\n"
                    "- which pages/slides it covers (source_range)\n"
                    'Return as JSON: {"topics": [{"title": "...", "description": "...", '
                    '"source_range": "..."}], "raw_summary": "..."}\n\n'
                    f"Course material content:\n\n{text}"
                ),
            },
        ]

        try:
            response: dict = await self.ai_router.get_json_response(messages)
            topics = [MaterialTopic(**t) for t in response.get("topics", [])]
            raw_summary: Optional[str] = response.get("raw_summary", "")
        except Exception:  # noqa: BLE001
            topics = []
            raw_summary = "Error: Failed to generate summary"

        summary = MaterialSummary(
            id=str(uuid.uuid4()),
            material_id=material_id,
            course_id=course_id,
            topics=topics,
            raw_summary=raw_summary,
        )

        await self.store.create_material_summary(
            {
                "material_id": material_id,
                "course_id": course_id,
                "summary_json": summary.model_dump_json(),
            }
        )

        return summary
