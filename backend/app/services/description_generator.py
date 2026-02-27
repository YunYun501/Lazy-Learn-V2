import json
from pathlib import Path

from app.models.description_schema import ChapterDescription, ConceptEntry
from app.services.description_manager import save_description

# Constant system prompt for DeepSeek cache hit optimization.
# MUST remain identical across all calls — 10x cheaper ($0.028/M vs $0.28/M tokens).
DESCRIPTION_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "Analyze the provided textbook chapter text and generate a structured description. "
    "For each concept, classify whether this chapter EXPLAINS it (introduces, derives, defines, proves) "
    "or USES it (applies in examples, problems, or design without explaining). "
    "Return JSON matching this exact schema:\n"
    "{\n"
    '  "chapter_title": "string",\n'
    '  "summary": "2-5 sentence summary of the chapter",\n'
    '  "key_concepts": [\n'
    '    {"name": "string", "aliases": ["string"], "classification": "EXPLAINS|USES", "description": "string"}\n'
    '  ],\n'
    '  "prerequisites": ["string"],\n'
    '  "mathematical_content": ["equation or theorem name as string"],\n'
    '  "has_figures": true,\n'
    '  "figure_descriptions": ["string"]\n'
    "}"
)

MAX_CHARS_PER_CHUNK = 200_000  # Split chapters longer than this


class DescriptionGenerator:
    """Generates AI-powered .md descriptions for textbook chapters."""

    def __init__(self, deepseek_provider, filesystem_manager):
        self.provider = deepseek_provider
        self.fs = filesystem_manager

    def _split_text(self, text: str) -> list[str]:
        """Split long text into chunks of at most MAX_CHARS_PER_CHUNK characters."""
        if len(text) <= MAX_CHARS_PER_CHUNK:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + MAX_CHARS_PER_CHUNK
            # Try to break at a paragraph boundary
            if end < len(text):
                boundary = text.rfind("\n\n", start, end)
                if boundary != -1 and boundary > start:
                    end = boundary
            chunks.append(text[start:end])
            start = end
        return chunks

    def _parse_ai_response(self, json_str: str) -> dict:
        """Parse the AI JSON response, stripping markdown code fences if present."""
        stripped = json_str.strip()
        if stripped.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = stripped.find("\n")
            if first_newline != -1:
                stripped = stripped[first_newline + 1:]
            # Remove closing fence
            if stripped.endswith("```"):
                stripped = stripped[:-3].rstrip()
        return json.loads(stripped)

    def _build_chapter_description(
        self,
        parsed: dict,
        textbook_id: str,
        chapter_num: str,
        page_range: tuple[int, int],
    ) -> ChapterDescription:
        """Convert parsed AI JSON dict into a ChapterDescription model."""
        key_concepts = []
        for c in parsed.get("key_concepts", []):
            classification = c.get("classification", "USES")
            if classification not in ("EXPLAINS", "USES"):
                classification = "USES"
            key_concepts.append(
                ConceptEntry(
                    name=c.get("name", ""),
                    aliases=c.get("aliases", []),
                    classification=classification,
                    description=c.get("description", ""),
                )
            )
        return ChapterDescription(
            source_textbook=textbook_id,
            chapter_number=chapter_num,
            chapter_title=parsed.get("chapter_title", f"Chapter {chapter_num}"),
            page_range=page_range,
            summary=parsed.get("summary", ""),
            key_concepts=key_concepts,
            prerequisites=parsed.get("prerequisites", []),
            mathematical_content=parsed.get("mathematical_content", []),
            has_figures=bool(parsed.get("has_figures", False)),
            figure_descriptions=parsed.get("figure_descriptions", []),
        )

    def _merge_descriptions(
        self,
        descriptions: list[ChapterDescription],
        textbook_id: str,
        chapter_num: str,
        page_range: tuple[int, int],
    ) -> ChapterDescription:
        """Merge multiple chunk descriptions into one."""
        if len(descriptions) == 1:
            return descriptions[0]

        # Merge key_concepts — deduplicate by name (case-insensitive)
        seen_names: set[str] = set()
        merged_concepts: list[ConceptEntry] = []
        for desc in descriptions:
            for concept in desc.key_concepts:
                key = concept.name.lower()
                if key not in seen_names:
                    seen_names.add(key)
                    merged_concepts.append(concept)

        # Merge mathematical_content — deduplicate
        seen_math: set[str] = set()
        merged_math: list[str] = []
        for desc in descriptions:
            for item in desc.mathematical_content:
                if item.lower() not in seen_math:
                    seen_math.add(item.lower())
                    merged_math.append(item)

        # Merge figure_descriptions
        merged_figures: list[str] = []
        for desc in descriptions:
            merged_figures.extend(desc.figure_descriptions)

        # Use first chunk's summary + ellipsis if multiple chunks
        summary = descriptions[0].summary
        if len(descriptions) > 1:
            summary = summary.rstrip(".") + "..."

        # Merge prerequisites — deduplicate
        seen_prereqs: set[str] = set()
        merged_prereqs: list[str] = []
        for desc in descriptions:
            for prereq in desc.prerequisites:
                if prereq.lower() not in seen_prereqs:
                    seen_prereqs.add(prereq.lower())
                    merged_prereqs.append(prereq)

        return ChapterDescription(
            source_textbook=textbook_id,
            chapter_number=chapter_num,
            chapter_title=descriptions[0].chapter_title,
            page_range=page_range,
            summary=summary,
            key_concepts=merged_concepts,
            prerequisites=merged_prereqs,
            mathematical_content=merged_math,
            has_figures=any(d.has_figures for d in descriptions),
            figure_descriptions=merged_figures,
        )

    async def generate_description(
        self,
        textbook_id: str,
        chapter_num: str,
        chapter_text: str,
        chapter_metadata: dict,
    ) -> ChapterDescription:
        """Generate a .md description for a single chapter.

        If the chapter text exceeds MAX_CHARS_PER_CHUNK, it is split into
        sections, each described separately, then merged into one description.
        """
        page_range = (
            chapter_metadata.get("page_start", 0),
            chapter_metadata.get("page_end", 0),
        )

        chunks = self._split_text(chapter_text)
        chunk_descriptions: list[ChapterDescription] = []

        for chunk in chunks:
            messages = [
                {"role": "system", "content": DESCRIPTION_SYSTEM_PROMPT},
                {"role": "user", "content": chunk},
            ]
            json_str = await self.provider.chat(messages, json_mode=True)
            parsed = self._parse_ai_response(json_str)
            desc = self._build_chapter_description(parsed, textbook_id, chapter_num, page_range)
            chunk_descriptions.append(desc)

        merged = self._merge_descriptions(chunk_descriptions, textbook_id, chapter_num, page_range)

        # Save to disk
        output_dir = self.fs.descriptions_dir / textbook_id
        save_description(merged, output_dir)

        return merged

    async def generate_all_descriptions(self, textbook_id: str) -> list[ChapterDescription]:
        """Generate descriptions for all chapters of a textbook.

        Reads chapter .txt files from {DATA_DIR}/textbooks/{textbook_id}/chapters/
        and generates a description for each one sequentially (to avoid rate limiting
        and maximise DeepSeek cache hits).
        """
        chapters_dir = self.fs.textbooks_dir / textbook_id / "chapters"
        if not chapters_dir.exists():
            return []

        results: list[ChapterDescription] = []
        for txt_file in sorted(chapters_dir.glob("*.txt")):
            chapter_num = txt_file.stem  # e.g. "1", "2", "3"
            chapter_text = txt_file.read_text(encoding="utf-8")
            desc = await self.generate_description(
                textbook_id=textbook_id,
                chapter_num=chapter_num,
                chapter_text=chapter_text,
                chapter_metadata={},
            )
            results.append(desc)

        return results
