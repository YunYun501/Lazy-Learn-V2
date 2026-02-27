"""Tests for the AI Match Categorizer (Task 15 — Step 2 of hybrid search)."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai_models import ClassifiedMatch
from app.services.keyword_search import SearchHit
from app.services.match_categorizer import (
    CATEGORIZATION_SYSTEM_PROMPT,
    CONFIDENCE_THRESHOLD,
    MatchCategorizer,
)


def _make_hit(source: str = "tb_001", chapter: str = "chapter_3", content: str = "Z-transform content") -> SearchHit:
    return SearchHit(
        file_path=f"/data/descriptions/{source}/{chapter}.md",
        matched_keyword="z-transform",
        context_snippet="Z-transform is explained here.",
        source_textbook=source,
        chapter=chapter,
        content=content,
    )


def _make_categorizer(responses: list[dict]) -> MatchCategorizer:
    provider = MagicMock()
    provider.chat = AsyncMock(side_effect=[json.dumps(r) for r in responses])
    return MatchCategorizer(deepseek_provider=provider)


# ---------------------------------------------------------------------------
# Test 1: EXPLAINS results sorted before USES
# ---------------------------------------------------------------------------

async def test_explains_sorted_before_uses():
    """EXPLAINS matches must appear before USES matches in the result list."""
    categorizer = _make_categorizer([
        {"classification": "USES", "confidence": 0.9, "reason": "Applied in examples"},
        {"classification": "EXPLAINS", "confidence": 0.8, "reason": "Introduced here"},
    ])
    hits = [_make_hit("tb_001", "chapter_1"), _make_hit("tb_001", "chapter_2")]
    results = await categorizer.categorize(hits, "Z-transform")

    assert len(results) == 2
    assert results[0].classification == "EXPLAINS"
    assert results[1].classification == "USES"


# ---------------------------------------------------------------------------
# Test 2: Low-confidence matches are filtered out
# ---------------------------------------------------------------------------

async def test_low_confidence_filtered_out():
    """Matches with confidence < CONFIDENCE_THRESHOLD must be excluded."""
    categorizer = _make_categorizer([
        {"classification": "EXPLAINS", "confidence": 0.1, "reason": "Barely mentioned"},
        {"classification": "USES", "confidence": 0.9, "reason": "Heavily applied"},
    ])
    hits = [_make_hit("tb_001", "chapter_1"), _make_hit("tb_001", "chapter_2")]
    results = await categorizer.categorize(hits, "Z-transform")

    assert len(results) == 1
    assert results[0].classification == "USES"
    assert results[0].confidence == 0.9


# ---------------------------------------------------------------------------
# Test 3: Full pipeline — categorize returns ClassifiedMatch objects
# ---------------------------------------------------------------------------

async def test_categorize_returns_classified_matches():
    """categorize() must return ClassifiedMatch objects with correct fields."""
    categorizer = _make_categorizer([
        {"classification": "EXPLAINS", "confidence": 0.95, "reason": "Full derivation provided"},
    ])
    hits = [_make_hit("tb_001", "chapter_3", "Z-transform is derived from scratch.")]
    results = await categorizer.categorize(hits, "Z-transform")

    assert len(results) == 1
    match = results[0]
    assert isinstance(match, ClassifiedMatch)
    assert match.classification == "EXPLAINS"
    assert match.confidence == 0.95
    assert match.source == "tb_001"
    assert match.chapter == "chapter_3"
    assert "derivation" in match.reason.lower()


# ---------------------------------------------------------------------------
# Test 4: System prompt contains EXPLAINS and USES guidance
# ---------------------------------------------------------------------------

def test_system_prompt_contains_classification_guidance():
    """CATEGORIZATION_SYSTEM_PROMPT must define EXPLAINS and USES clearly."""
    assert "EXPLAINS" in CATEGORIZATION_SYSTEM_PROMPT
    assert "USES" in CATEGORIZATION_SYSTEM_PROMPT
    assert "confidence" in CATEGORIZATION_SYSTEM_PROMPT
    assert CONFIDENCE_THRESHOLD == 0.3
