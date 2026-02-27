"""Tests for the AI Description Generator (Task 10)."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.description_generator import (
    DESCRIPTION_SYSTEM_PROMPT,
    MAX_CHARS_PER_CHUNK,
    DescriptionGenerator,
)
from app.models.description_schema import ChapterDescription


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ai_response(
    chapter_title: str = "Test Chapter",
    summary: str = "A test summary.",
    concepts: list[dict] | None = None,
) -> str:
    """Return a valid JSON string that mimics a DeepSeek response."""
    if concepts is None:
        concepts = [
            {
                "name": "Z-transform",
                "aliases": ["z transform", "ZT"],
                "classification": "EXPLAINS",
                "description": "Introduced and derived in this chapter.",
            }
        ]
    return json.dumps(
        {
            "chapter_title": chapter_title,
            "summary": summary,
            "key_concepts": concepts,
            "prerequisites": ["Laplace transform"],
            "mathematical_content": ["Z-transform definition"],
            "has_figures": True,
            "figure_descriptions": ["Figure 1: Z-plane diagram"],
        }
    )


def _make_generator(tmp_path: Path, mock_chat_return: str | list[str]) -> DescriptionGenerator:
    """Create a DescriptionGenerator with a mocked DeepSeek provider."""
    provider = MagicMock()
    if isinstance(mock_chat_return, list):
        provider.chat = AsyncMock(side_effect=mock_chat_return)
    else:
        provider.chat = AsyncMock(return_value=mock_chat_return)

    fs = MagicMock()
    fs.descriptions_dir = tmp_path / "descriptions"
    fs.textbooks_dir = tmp_path / "textbooks"
    fs.descriptions_dir.mkdir(parents=True, exist_ok=True)

    return DescriptionGenerator(deepseek_provider=provider, filesystem_manager=fs)


# ---------------------------------------------------------------------------
# Test 1: DESCRIPTION_SYSTEM_PROMPT contains required schema keywords
# ---------------------------------------------------------------------------

def test_prompt_construction_includes_schema():
    """DESCRIPTION_SYSTEM_PROMPT must contain EXPLAINS, USES, and JSON schema keys."""
    assert "EXPLAINS" in DESCRIPTION_SYSTEM_PROMPT
    assert "USES" in DESCRIPTION_SYSTEM_PROMPT
    assert "chapter_title" in DESCRIPTION_SYSTEM_PROMPT
    assert "key_concepts" in DESCRIPTION_SYSTEM_PROMPT
    assert "classification" in DESCRIPTION_SYSTEM_PROMPT
    assert "mathematical_content" in DESCRIPTION_SYSTEM_PROMPT
    assert "summary" in DESCRIPTION_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Test 2: AI response is parsed into a correct ChapterDescription
# ---------------------------------------------------------------------------

async def test_ai_response_parsing(tmp_path: Path):
    """generate_description() must parse the AI JSON into a valid ChapterDescription."""
    ai_json = _make_ai_response(
        chapter_title="The Z-Transform",
        summary="This chapter introduces the Z-transform.",
        concepts=[
            {
                "name": "Z-transform",
                "aliases": ["ZT"],
                "classification": "EXPLAINS",
                "description": "Defined and derived here.",
            },
            {
                "name": "Pole-zero plot",
                "aliases": [],
                "classification": "USES",
                "description": "Used in examples.",
            },
        ],
    )

    generator = _make_generator(tmp_path, ai_json)

    desc = await generator.generate_description(
        textbook_id="tb_001",
        chapter_num="3",
        chapter_text="Some chapter text about Z-transforms.",
        chapter_metadata={"page_start": 45, "page_end": 72},
    )

    assert isinstance(desc, ChapterDescription)
    assert desc.chapter_title == "The Z-Transform"
    assert "Z-transform" in desc.summary
    assert desc.page_range == (45, 72)
    assert len(desc.key_concepts) == 2

    explains = [c for c in desc.key_concepts if c.classification == "EXPLAINS"]
    uses = [c for c in desc.key_concepts if c.classification == "USES"]
    assert len(explains) == 1
    assert explains[0].name == "Z-transform"
    assert len(uses) == 1
    assert uses[0].name == "Pole-zero plot"

    # Verify .md file was saved
    md_file = tmp_path / "descriptions" / "tb_001" / "chapter_3.md"
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert "[EXPLAINS]" in content
    assert "[USES]" in content


# ---------------------------------------------------------------------------
# Test 3: Long chapters are split into multiple chunks before calling AI
# ---------------------------------------------------------------------------

async def test_long_chapter_splitting(tmp_path: Path):
    """Chapters longer than MAX_CHARS_PER_CHUNK must be split; AI called once per chunk."""
    # Create text that is 2.5x the chunk limit
    long_text = "A" * int(MAX_CHARS_PER_CHUNK * 2.5)

    ai_json = _make_ai_response()
    generator = _make_generator(tmp_path, ai_json)

    await generator.generate_description(
        textbook_id="tb_002",
        chapter_num="1",
        chapter_text=long_text,
        chapter_metadata={},
    )

    # With 2.5x the limit, we expect 3 chunks → 3 AI calls
    call_count = generator.provider.chat.call_count
    assert call_count >= 2, f"Expected at least 2 AI calls for long chapter, got {call_count}"


# ---------------------------------------------------------------------------
# Test 4: Merging descriptions from multiple chunks combines concepts
# ---------------------------------------------------------------------------

async def test_merge_descriptions_combines_concepts(tmp_path: Path):
    """Concepts from all chunks must appear in the merged description."""
    chunk1_json = _make_ai_response(
        chapter_title="Control Systems",
        summary="First part covers state-space.",
        concepts=[
            {
                "name": "State-space representation",
                "aliases": ["state space"],
                "classification": "EXPLAINS",
                "description": "Introduced in part 1.",
            }
        ],
    )
    chunk2_json = _make_ai_response(
        chapter_title="Control Systems",
        summary="Second part covers transfer functions.",
        concepts=[
            {
                "name": "Transfer function",
                "aliases": ["TF"],
                "classification": "EXPLAINS",
                "description": "Introduced in part 2.",
            }
        ],
    )

    # Two chunks → two different AI responses
    long_text = "B" * int(MAX_CHARS_PER_CHUNK * 1.5)
    generator = _make_generator(tmp_path, [chunk1_json, chunk2_json])

    desc = await generator.generate_description(
        textbook_id="tb_003",
        chapter_num="2",
        chapter_text=long_text,
        chapter_metadata={},
    )

    concept_names = [c.name for c in desc.key_concepts]
    assert "State-space representation" in concept_names, (
        f"Expected 'State-space representation' in {concept_names}"
    )
    assert "Transfer function" in concept_names, (
        f"Expected 'Transfer function' in {concept_names}"
    )
    # Summary should end with "..." since multiple chunks
    assert desc.summary.endswith("...")
