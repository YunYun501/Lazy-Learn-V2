"""Material Organizer service — auto-categorize downloaded course files using AI."""
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Module-level constant for DeepSeek cache hit optimization.
# MUST remain identical across all calls — 10x cheaper ($0.028/M vs $0.28/M tokens).
CLASSIFY_SYSTEM_PROMPT = (
    "You are an academic document classifier. "
    "Your task is to classify academic documents into predefined categories based on their content.\n\n"
    "Classify the document into ONE of these categories:\n"
    "- lecture_slides: Presentation slides used in lectures\n"
    "- tutorial_questions: Tutorial or assignment questions or problems for students to solve\n"
    "- tutorial_solutions: Solutions or answer keys to tutorial or assignment questions\n"
    "- past_exam_papers: Past examination papers or quizzes\n"
    "- lab_manual: Laboratory manuals or lab instructions\n"
    "- reference_notes: Reference material, notes, or supplementary reading\n"
    "- other: Does not fit any of the above categories\n\n"
    "Also extract metadata if visible:\n"
    "- course_code: The course code (e.g., EE2010, CS101) — null if not found\n"
    "- title: The document title — null if not found\n"
    "- date: Any date information visible — null if not found\n\n"
    'Return ONLY valid JSON with this exact schema:\n'
    '{"category": "one_of_the_categories_above", "course_code": "string_or_null", '
    '"title": "string_or_null", "date": "string_or_null"}'
)

# Category → subdirectory folder mapping
CATEGORY_FOLDER_MAP: dict[str, str] = {
    "lecture_slides": "lectures",
    "tutorial_questions": "tutorials",
    "tutorial_solutions": "tutorials/solutions",
    "past_exam_papers": "exams",
    "lab_manual": "labs",
    "reference_notes": "notes",
    "other": "other",
}

SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx"}

# Max chars extracted from a document for classification (first few pages)
MAX_CHARS_FOR_CLASSIFICATION = 5_000


@dataclass
class OrganizedFile:
    """Represents a single successfully organized file."""

    source_path: str
    dest_path: str
    category: str
    course_code: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    description_path: Optional[str] = None


@dataclass
class OrganizationResult:
    """Result of a full organize_materials() call."""

    organized_files: list[OrganizedFile] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    total_found: int = 0
    total_organized: int = 0
    total_skipped: int = 0

    @property
    def categories(self) -> dict[str, int]:
        """Return count of files per category."""
        counts: dict[str, int] = {}
        for f in self.organized_files:
            counts[f.category] = counts.get(f.category, 0) + 1
        return counts


class MaterialOrganizer:
    """Auto-categorizes downloaded course files (PDF/PPTX/DOCX) using AI classification.

    Files are COPIED (not moved) into categorized subdirectories under dest_dir.
    A brief .md description is generated for each organized file.
    Duplicate filenames already present in dest_dir are skipped.
    """

    def __init__(self, ai_provider, document_parser=None):
        self.ai = ai_provider
        self.parser = document_parser

    # ------------------------------------------------------------------
    # Text extraction helpers
    # ------------------------------------------------------------------

    def _extract_text_from_pdf(self, filepath: str, max_chars: int = MAX_CHARS_FOR_CLASSIFICATION) -> str:
        """Extract text from the first few pages of a PDF using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF  # noqa: PLC0415

            doc = fitz.open(filepath)
            text_parts: list[str] = []
            total_chars = 0
            for page_num in range(min(5, len(doc))):  # First 5 pages max
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
        self, filepath: str, max_chars: int = MAX_CHARS_FOR_CLASSIFICATION
    ) -> str:
        """Extract text from PPTX/DOCX using the injected document parser."""
        if self.parser is None:
            return ""
        try:
            parsed = self.parser.parse(filepath)
            text_parts: list[str] = []
            total_chars = 0
            for chapter in parsed.chapters[:10]:  # First 10 slides/sections
                chapter_text = chapter.get("text", "")
                text_parts.append(chapter_text)
                total_chars += len(chapter_text)
                if total_chars >= max_chars:
                    break
            return "\n".join(text_parts)[:max_chars]
        except Exception as exc:  # noqa: BLE001
            return f"[Document extraction error: {exc}]"

    def _extract_text(self, filepath: str) -> str:
        """Dispatch text extraction by file extension."""
        ext = Path(filepath).suffix.lower()
        if ext == ".pdf":
            return self._extract_text_from_pdf(filepath)
        if ext in (".pptx", ".docx"):
            return self._extract_text_from_document(filepath)
        return ""

    # ------------------------------------------------------------------
    # AI classification
    # ------------------------------------------------------------------

    def _parse_ai_response(self, json_str: str) -> dict:
        """Parse AI JSON response, stripping markdown code fences if present."""
        stripped = json_str.strip()
        if stripped.startswith("```"):
            first_newline = stripped.find("\n")
            if first_newline != -1:
                stripped = stripped[first_newline + 1:]
            if stripped.endswith("```"):
                stripped = stripped[:-3].rstrip()
        return json.loads(stripped)

    async def _classify_document(self, filepath: str) -> dict:
        """Extract text from document and classify it with DeepSeek."""
        text = self._extract_text(filepath)
        if not text:
            return {"category": "other", "course_code": None, "title": None, "date": None}

        messages = [
            {"role": "system", "content": CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Document text preview:\n\n{text}"},
        ]
        try:
            json_str = await self.ai.chat(messages, json_mode=True)
            return self._parse_ai_response(json_str)
        except Exception:  # noqa: BLE001
            return {"category": "other", "course_code": None, "title": None, "date": None}

    # ------------------------------------------------------------------
    # Markdown description generation
    # ------------------------------------------------------------------

    def _generate_description(self, filepath: str, classification: dict) -> str:
        """Generate a brief .md description for the given file."""
        path = Path(filepath)
        ext = path.suffix.lower()

        category = classification.get("category", "other")
        course_code = classification.get("course_code") or "Unknown"
        title = classification.get("title") or path.stem
        date = classification.get("date") or "Unknown"

        lines: list[str] = [
            f"# {title}",
            "",
            f"**File:** `{path.name}`  ",
            f"**Category:** {category}  ",
            f"**Course Code:** {course_code}  ",
            f"**Date:** {date}  ",
            "",
        ]

        if ext in (".pptx", ".docx") and self.parser is not None:
            try:
                parsed = self.parser.parse(filepath)
                if ext == ".pptx":
                    lines.append(f"**Total Slides:** {parsed.total_pages}  ")
                    lines.append("")
                    lines.append("## Slide Breakdown")
                    lines.append("")
                    for chapter in parsed.chapters[:20]:
                        slide_num = chapter.get("number", "?")
                        slide_text = chapter.get("text", "").strip()
                        preview = slide_text[:100] + "..." if len(slide_text) > 100 else slide_text
                        lines.append(f"- **Slide {slide_num}:** {preview}")
                else:  # .docx
                    lines.append(f"**Total Sections:** {parsed.total_pages}  ")
                    lines.append("")
                    lines.append("## Section Breakdown")
                    lines.append("")
                    for chapter in parsed.chapters[:20]:
                        section_title = chapter.get("title", "Section")
                        section_text = chapter.get("text", "").strip()
                        preview = section_text[:100] + "..." if len(section_text) > 100 else section_text
                        lines.append(f"- **{section_title}:** {preview}")
            except Exception:  # noqa: BLE001
                pass
        elif ext == ".pdf":
            try:
                import fitz  # noqa: PLC0415

                doc = fitz.open(filepath)
                page_count = len(doc)
                doc.close()
                lines.append(f"**Total Pages:** {page_count}  ")
                lines.append("")
                lines.append("## Page Breakdown")
                lines.append("")
                lines.append(f"This PDF contains {page_count} pages.")
            except Exception:  # noqa: BLE001
                pass

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    async def organize_materials(self, source_dir: str, dest_dir: str) -> OrganizationResult:
        """Scan source_dir for PDF/PPTX/DOCX files and copy them into categorized subdirs.

        - Files are COPIED (not moved) to preserve originals.
        - Duplicate detection: files already present in dest_dir (by filename) are skipped.
        - A .md description is generated alongside each copied file.
        """
        source_path = Path(source_dir)
        dest_path = Path(dest_dir)

        result = OrganizationResult()

        # Collect all supported files, deduplicate by resolved path
        seen_paths: set[Path] = set()
        unique_files: list[Path] = []
        for ext in SUPPORTED_EXTENSIONS:
            for file_path in source_path.glob(f"*{ext}"):
                resolved = file_path.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    unique_files.append(file_path)
            # Also handle uppercase extensions on case-sensitive filesystems
            for file_path in source_path.glob(f"*{ext.upper()}"):
                resolved = file_path.resolve()
                if resolved not in seen_paths:
                    seen_paths.add(resolved)
                    unique_files.append(file_path)

        result.total_found = len(unique_files)

        for file_path in unique_files:
            # AI classification
            classification = await self._classify_document(str(file_path))
            category = classification.get("category", "other")

            # Validate category falls within known set
            if category not in CATEGORY_FOLDER_MAP:
                category = "other"

            # Determine target directory
            folder_name = CATEGORY_FOLDER_MAP[category]
            target_dir = dest_path / folder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            target_file = target_dir / file_path.name

            # Duplicate detection: skip if filename already exists in target dir
            if target_file.exists():
                result.skipped_files.append(str(file_path))
                result.total_skipped += 1
                continue

            # Copy file (preserving metadata)
            shutil.copy2(str(file_path), str(target_file))

            # Generate .md description
            description_md = self._generate_description(str(file_path), classification)
            desc_file = target_dir / f"{file_path.stem}.md"
            desc_file.write_text(description_md, encoding="utf-8")

            result.organized_files.append(
                OrganizedFile(
                    source_path=str(file_path),
                    dest_path=str(target_file),
                    category=category,
                    course_code=classification.get("course_code"),
                    title=classification.get("title"),
                    date=classification.get("date"),
                    description_path=str(desc_file),
                )
            )
            result.total_organized += 1

        return result
