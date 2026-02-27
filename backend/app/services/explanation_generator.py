"""Step 4 of the hybrid search pipeline: AI explanation generator with streaming.

Uses deepseek-reasoner (64K output) for detailed, structured explanations
with LaTeX equations and source citations.
"""
from pathlib import Path
from typing import AsyncGenerator

from app.services.deepseek_provider import DeepSeekProvider, REASONER_MODEL

# Constant system prompt for DeepSeek cache hit optimization.
EXPLANATION_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "Using the textbook content provided, explain the concept to the student. "
    "Structure your response as:\n"
    "1) Introduction/Definition\n"
    "2) Mathematical derivation with LaTeX\n"
    "3) Intuitive explanation\n"
    "4) Key properties/theorems\n"
    "5) Common applications\n\n"
    "After each section, cite the source: [Source: textbook_title, Ch.X.Y, p.N]. "
    "Use LaTeX for ALL equations: inline $...$ and display $$...$$. "
    "Be thorough but clear."
)

# Maximum characters of chapter content to send (to stay within context window)
MAX_CONTENT_CHARS = 100_000


class SelectedChapter:
    """A chapter selected by the user for explanation generation."""

    def __init__(
        self,
        textbook_id: str,
        chapter_num: str,
        classification: str = "EXPLAINS",
        textbook_title: str = "",
    ):
        self.textbook_id = textbook_id
        self.chapter_num = chapter_num
        self.classification = classification  # "EXPLAINS" or "USES"
        self.textbook_title = textbook_title or textbook_id


class ExplanationGenerator:
    """Step 4: Generate streaming AI explanations from selected textbook chapters."""

    def __init__(self, deepseek_provider: DeepSeekProvider, data_dir: Path):
        self.provider = deepseek_provider
        self.data_dir = data_dir

    def _read_chapter_text(self, textbook_id: str, chapter_num: str) -> str:
        """Read the extracted chapter text from disk."""
        chapter_path = self.data_dir / "textbooks" / textbook_id / "chapters" / f"{chapter_num}.txt"
        if chapter_path.exists():
            return chapter_path.read_text(encoding="utf-8")
        return ""

    def _build_content(self, chapters: list[SelectedChapter]) -> str:
        """Build the combined content string from selected chapters.

        Prioritizes EXPLAINS chapters. Truncates USES chapters if total
        content would exceed MAX_CONTENT_CHARS.
        """
        # Sort: EXPLAINS first, then USES
        sorted_chapters = sorted(
            chapters,
            key=lambda c: (0 if c.classification == "EXPLAINS" else 1)
        )

        parts: list[str] = []
        total_chars = 0

        for chapter in sorted_chapters:
            text = self._read_chapter_text(chapter.textbook_id, chapter.chapter_num)
            if not text:
                continue

            header = (
                f"\n\n=== Source: {chapter.textbook_title}, "
                f"Chapter {chapter.chapter_num} ===\n"
            )
            chunk = header + text

            if total_chars + len(chunk) > MAX_CONTENT_CHARS:
                # Truncate to fit
                remaining = MAX_CONTENT_CHARS - total_chars - len(header) - len("\n[...truncated...]")
                truncation_marker = "\n[...truncated...]"
                if remaining > 500:
                    parts.append(header + text[:remaining] + "\n[...truncated...]")
                break

            parts.append(chunk)
            total_chars += len(chunk)

        return "\n".join(parts)

    async def generate_explanation(
        self,
        selected_chapters: list[SelectedChapter],
        query: str,
    ) -> AsyncGenerator[str, None]:
        """Stream an AI explanation for the selected chapters and query.

        Uses deepseek-reasoner for 64K output capacity.
        Yields SSE-formatted chunks.
        """
        content = self._build_content(selected_chapters)

        messages = [
            {"role": "system", "content": EXPLANATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Query: {query}\n\nTextbook content:\n{content}",
            },
        ]

        payload = {
            "model": REASONER_MODEL,
            "messages": messages,
            "stream": True,
        }

        async for chunk in self.provider._stream_response(payload):
            yield chunk
