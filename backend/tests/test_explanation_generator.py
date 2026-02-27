"""Tests for ExplanationGenerator (Step 4 of the hybrid search pipeline)."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.services.explanation_generator import (
    ExplanationGenerator,
    SelectedChapter,
    EXPLANATION_SYSTEM_PROMPT,
    MAX_CONTENT_CHARS,
)


def test_explanation_system_prompt_contains_source_citation_instruction():
    """System prompt must instruct the AI to cite sources after each section."""
    assert "cite" in EXPLANATION_SYSTEM_PROMPT.lower(), (
        "EXPLANATION_SYSTEM_PROMPT must contain citation instructions"
    )
    assert "source" in EXPLANATION_SYSTEM_PROMPT.lower(), (
        "EXPLANATION_SYSTEM_PROMPT must reference 'source' for attribution"
    )


async def test_streaming_yields_multiple_chunks(tmp_path):
    """generate_explanation() must yield every chunk from _stream_response."""

    async def mock_stream(payload):
        for chunk in ["chunk1", "chunk2", "chunk3"]:
            yield chunk

    provider = MagicMock()
    provider._stream_response = mock_stream

    generator = ExplanationGenerator(deepseek_provider=provider, data_dir=tmp_path)

    # Create a dummy chapter text file so _read_chapter_text returns content
    textbook_dir = tmp_path / "textbooks" / "tb1" / "chapters"
    textbook_dir.mkdir(parents=True)
    (textbook_dir / "1.txt").write_text("Chapter 1 content about Z-transforms.", encoding="utf-8")

    chapter = SelectedChapter(
        textbook_id="tb1",
        chapter_num="1",
        classification="EXPLAINS",
        textbook_title="Digital Control Systems",
    )

    chunks = []
    async for chunk in generator.generate_explanation([chapter], "Explain Z-transform"):
        chunks.append(chunk)

    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}: {chunks}"
    assert chunks == ["chunk1", "chunk2", "chunk3"]


async def test_content_overflow_truncation(tmp_path):
    """_build_content() must truncate chapters that exceed MAX_CONTENT_CHARS."""
    provider = MagicMock()

    generator = ExplanationGenerator(deepseek_provider=provider, data_dir=tmp_path)

    # Create two chapters: first fills 90% of the limit, second would overflow
    textbook_dir = tmp_path / "textbooks" / "tb1" / "chapters"
    textbook_dir.mkdir(parents=True)
    large = int(MAX_CONTENT_CHARS * 0.9)
    (textbook_dir / "1.txt").write_text("A" * large, encoding="utf-8")
    # Second chapter is large enough to push total well over the limit
    (textbook_dir / "2.txt").write_text("B" * large, encoding="utf-8")

    chapters = [
        SelectedChapter(textbook_id="tb1", chapter_num="1", classification="EXPLAINS"),
        SelectedChapter(textbook_id="tb1", chapter_num="2", classification="EXPLAINS"),
    ]

    content = generator._build_content(chapters)

    # Allow a small overhead for headers and join separators (< 200 bytes)
    assert len(content) <= MAX_CONTENT_CHARS + 200, (
        f"Content length {len(content)} far exceeds MAX_CONTENT_CHARS {MAX_CONTENT_CHARS}"
    )
    assert "[...truncated...]" in content, "Truncated content must include truncation marker"
