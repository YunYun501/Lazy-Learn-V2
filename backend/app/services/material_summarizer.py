"""Material Summarizer service — extract text from course materials and categorize via AI."""
import uuid
from pathlib import Path
from typing import Optional

from app.models.pipeline_models import MaterialSummary, MaterialTopic
from app.services.storage import MetadataStore

SUMMARIZE_SYSTEM_PROMPT = (
    "You are an academic course material analyzer. "
    "Your task is to scan a document page-by-page (or slide-by-slide) and group "
    "consecutive pages/slides into distinct topics.\n\n"
    "Rules:\n"
    "1. Every page/slide MUST belong to exactly one topic — no gaps.\n"
    "2. Use the page/slide markers (e.g. '--- Page 3 ---' or '--- Slide 5 ---') "
    "to determine exact ranges.\n"
    "3. Merge consecutive pages/slides that cover the SAME topic into one entry.\n"
    "4. source_range must use the document's own unit: 'slides 1-3' for presentations, "
    "'pages 1-5' for PDFs/documents.\n"
    "5. If a single page/slide covers a topic alone, write e.g. 'slide 4' (not 'slides 4-4').\n\n"
    "For each topic provide:\n"
    "- title: A concise topic title\n"
    "- description: 2-3 sentence description of the content\n"
    "- source_range: Exact page/slide range (e.g. 'slides 1-3', 'pages 12-18')\n\n"
    "Also provide a brief raw_summary of the entire document (2-3 sentences).\n\n"
    'Return ONLY valid JSON:\n'
    '{"topics": [{"title": "...", "description": "...", "source_range": "..."}], '
    '"raw_summary": "..."}'
)

MAX_CHARS_FOR_SUMMARY = 50_000


class MaterialSummarizer:
    """Extracts text from course materials (PDF/PPTX/DOCX) and categorizes via AI.

    Extracts text per page/slide with markers so the AI can produce precise
    source ranges (e.g. 'slides 1-3 is Topic A, slides 4-5 is Topic B').
    One AI call is made per document.
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
                marker = f"\n--- Page {page_num + 1} ---\n"
                page_text = doc[page_num].get_text()
                text_parts.append(marker + page_text)
                total_chars += len(marker) + len(page_text)
                if total_chars >= max_chars:
                    break
            doc.close()
            return "".join(text_parts)[:max_chars]
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
                slide_num = chapter.get("number", chapter.get("page_start", "?"))
                marker = f"\n--- Slide {slide_num} ---\n"
                chapter_text = chapter.get("text", "")
                text_parts.append(marker + chapter_text)
                total_chars += len(marker) + len(chapter_text)
                if total_chars >= max_chars:
                    break
            return "".join(text_parts)[:max_chars]
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

        # Detect document type for the user prompt
        ext = Path(file_path).suffix.lower()
        unit = "slides" if ext == ".pptx" else "pages"

        messages = [
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Analyze this course material and categorize every {unit} into topics.\n"
                    f"Each {unit[:-1]} must belong to exactly one topic. "
                    f"Group consecutive {unit} that cover the same topic.\n"
                    f"Use '{unit} X-Y' format for source_range.\n\n"
                    f"Document content:\n{text}"
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
