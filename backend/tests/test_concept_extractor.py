"""Tests for the AI Concept Extractor (Task 13 — Step 0 of hybrid search)."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai_models import ConceptExtraction
from app.services.concept_extractor import (
    CONCEPT_EXTRACTION_SYSTEM_PROMPT,
    ConceptExtractor,
)


def _make_extractor(mock_response: dict) -> ConceptExtractor:
    provider = MagicMock()
    provider.chat = AsyncMock(return_value=json.dumps(mock_response))
    return ConceptExtractor(deepseek_provider=provider)


# ---------------------------------------------------------------------------
# Test 1: Explicit concept extraction
# ---------------------------------------------------------------------------

async def test_explicit_concept_extraction():
    """Explicitly named concepts must be extracted from the query."""
    extractor = _make_extractor(
        {"concepts": ["Z-transform"], "equations": [], "related_terms": ["ZT"]}
    )
    result = await extractor.extract("Explain the Z-transform")
    assert isinstance(result, ConceptExtraction)
    assert "Z-transform" in result.concepts


# ---------------------------------------------------------------------------
# Test 2: Equation form recognition
# ---------------------------------------------------------------------------

async def test_equation_form_recognition():
    """Z-transform must be identified from an equation even without explicit naming."""
    extractor = _make_extractor(
        {
            "concepts": ["Z-transform"],
            "equations": ["discrete transfer function"],
            "related_terms": [],
        }
    )
    result = await extractor.extract("How do I solve Y(z) = 0.5z/(z-0.8)?")
    assert "Z-transform" in result.concepts
    assert "discrete transfer function" in result.equations


# ---------------------------------------------------------------------------
# Test 3: Vague query returns valid ConceptExtraction (no crash)
# ---------------------------------------------------------------------------

async def test_vague_query_returns_valid_result():
    """A vague query must return a valid ConceptExtraction without crashing."""
    extractor = _make_extractor(
        {
            "concepts": [],
            "equations": [],
            "related_terms": ["discrete systems", "difference equations"],
        }
    )
    result = await extractor.extract("explain this equation for discrete systems")
    assert isinstance(result, ConceptExtraction)
    # related_terms are not stored in ConceptExtraction — only concepts + equations
    assert result.concepts == []
    assert result.equations == []


# ---------------------------------------------------------------------------
# Test 4: System prompt contains required keywords
# ---------------------------------------------------------------------------

def test_system_prompt_contains_required_keywords():
    """CONCEPT_EXTRACTION_SYSTEM_PROMPT must guide equation form recognition."""
    assert "EXPLAINS" not in CONCEPT_EXTRACTION_SYSTEM_PROMPT  # That's for descriptions
    assert "equation FORMS" in CONCEPT_EXTRACTION_SYSTEM_PROMPT
    assert "concepts" in CONCEPT_EXTRACTION_SYSTEM_PROMPT
    assert "Z-transform" in CONCEPT_EXTRACTION_SYSTEM_PROMPT
