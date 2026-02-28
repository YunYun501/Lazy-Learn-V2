"""Tests for the MaterialSummarizer service (TDD — tests written first)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.pipeline_models import MaterialSummary, MaterialTopic
from app.services.material_summarizer import MaterialSummarizer


# ---------------------------------------------------------------------------
# Shared mock AI response fixture
# ---------------------------------------------------------------------------

MOCK_DEEPSEEK_RESPONSE = {
    "topics": [
        {
            "title": "Introduction to Neural Networks",
            "description": "This section covers the foundational concepts of neural networks including perceptrons and activation functions.",
            "source_range": "pages 1-5",
        },
        {
            "title": "Backpropagation Algorithm",
            "description": "Detailed walkthrough of the backpropagation algorithm used to train neural networks.",
            "source_range": "pages 6-12",
        },
    ],
    "raw_summary": "This document introduces neural network fundamentals and the backpropagation training algorithm.",
}


def _make_store() -> AsyncMock:
    """Return a mocked MetadataStore."""
    store = AsyncMock()
    store.create_material_summary = AsyncMock(return_value="summary-id-mock")
    return store


def _make_ai_router(response: dict = MOCK_DEEPSEEK_RESPONSE) -> MagicMock:
    """Return a mocked ai_router with get_json_response stubbed."""
    ai_router = MagicMock()
    ai_router.get_json_response = AsyncMock(return_value=response)
    return ai_router


def _make_summarizer(
    ai_router=None, store=None, document_parser=None
) -> MaterialSummarizer:
    """Create a MaterialSummarizer with fully mocked dependencies."""
    return MaterialSummarizer(
        store=store or _make_store(),
        ai_router=ai_router or _make_ai_router(),
        document_parser=document_parser,
    )


# ---------------------------------------------------------------------------
# Test 1 — PDF material → structured summary with topics
# ---------------------------------------------------------------------------


async def test_summarize_pdf_material(tmp_path):
    """Mock DeepSeek → returns structured MaterialSummary with topics for a PDF."""
    fake_pdf = tmp_path / "lecture.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake content")

    summarizer = _make_summarizer()

    with patch.object(summarizer, "_extract_text", return_value="Neural networks are..."):
        result = await summarizer.summarize(
            material_id="mat-001",
            file_path=str(fake_pdf),
            course_id="course-123",
        )

    assert isinstance(result, MaterialSummary)
    assert result.material_id == "mat-001"
    assert result.course_id == "course-123"
    assert len(result.topics) == 2
    assert result.topics[0].title == "Introduction to Neural Networks"
    assert result.raw_summary is not None


# ---------------------------------------------------------------------------
# Test 2 — PPTX material → handles slide-based content
# ---------------------------------------------------------------------------


async def test_summarize_pptx_material(tmp_path):
    """Mock DeepSeek → handles slide-based content correctly for a PPTX."""
    fake_pptx = tmp_path / "slides.pptx"
    fake_pptx.write_bytes(b"PK fake pptx")

    # Build a mock document parser that mimics real slide parsing
    mock_chapter = MagicMock()
    mock_chapter.get = MagicMock(
        side_effect=lambda key, default="": (
            "Slide 1: Introduction to Neural Networks"
            if key == "text"
            else default
        )
    )
    mock_parsed = MagicMock()
    mock_parsed.chapters = [mock_chapter]

    mock_parser = MagicMock()
    mock_parser.parse = MagicMock(return_value=mock_parsed)

    ai_router = _make_ai_router()
    store = _make_store()

    summarizer = MaterialSummarizer(
        store=store, ai_router=ai_router, document_parser=mock_parser
    )

    result = await summarizer.summarize(
        material_id="mat-002",
        file_path=str(fake_pptx),
        course_id="course-456",
    )

    assert isinstance(result, MaterialSummary)
    assert result.material_id == "mat-002"
    assert len(result.topics) == 2
    # Parser must have been invoked for the PPTX file
    mock_parser.parse.assert_called_once_with(str(fake_pptx))
    # AI router was called exactly once (one call per document)
    ai_router.get_json_response.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3 — Summary stored persistently via MetadataStore
# ---------------------------------------------------------------------------


async def test_summary_stored_persistently(tmp_path):
    """After summarization → summary is persisted in DB via MetadataStore."""
    fake_pdf = tmp_path / "notes.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")

    store = _make_store()
    summarizer = _make_summarizer(store=store)

    with patch.object(summarizer, "_extract_text", return_value="Course content here."):
        await summarizer.summarize(
            material_id="mat-003",
            file_path=str(fake_pdf),
            course_id="course-789",
        )

    store.create_material_summary.assert_called_once()
    saved = store.create_material_summary.call_args[0][0]
    assert saved["material_id"] == "mat-003"
    assert saved["course_id"] == "course-789"
    assert "summary_json" in saved
    assert saved["summary_json"]  # non-empty string


# ---------------------------------------------------------------------------
# Test 4 — Empty content → graceful error, no crash
# ---------------------------------------------------------------------------


async def test_empty_content_returns_error(tmp_path):
    """No extractable text → returns graceful error result, does NOT crash."""
    fake_pdf = tmp_path / "empty.pdf"
    fake_pdf.write_bytes(b"")

    ai_router = _make_ai_router()
    store = _make_store()
    summarizer = MaterialSummarizer(store=store, ai_router=ai_router)

    with patch.object(summarizer, "_extract_text", return_value=""):
        result = await summarizer.summarize(
            material_id="mat-004",
            file_path=str(fake_pdf),
            course_id="course-101",
        )

    # Must return a valid MaterialSummary (not raise)
    assert isinstance(result, MaterialSummary)
    assert result.material_id == "mat-004"
    assert result.topics == []
    assert result.raw_summary is not None
    # DeepSeek must NOT be called when there is no content to summarize
    ai_router.get_json_response.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — Summary JSON has topics with title + description + source_range
# ---------------------------------------------------------------------------


async def test_summary_format_has_topics(tmp_path):
    """Summary JSON contains topics list with title, description, and source_range."""
    fake_pdf = tmp_path / "ml_lecture.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4")

    detailed_response = {
        "topics": [
            {
                "title": "Topic 1: ML Basics",
                "description": "Introduction to machine learning fundamentals and terminology.",
                "source_range": "slides 1-3",
            },
            {
                "title": "Topic 2: Linear Regression",
                "description": "Deep dive into linear regression models and cost functions.",
                "source_range": "slides 4-8",
            },
            {
                "title": "Topic 3: Decision Trees",
                "description": "Overview of decision tree algorithms and pruning strategies.",
                "source_range": "slides 9-12",
            },
        ],
        "raw_summary": "Comprehensive ML overview covering basics, regression, and decision trees.",
    }

    ai_router = _make_ai_router(response=detailed_response)
    store = _make_store()
    summarizer = MaterialSummarizer(store=store, ai_router=ai_router)

    with patch.object(
        summarizer, "_extract_text", return_value="Machine learning content..."
    ):
        result = await summarizer.summarize(
            material_id="mat-005",
            file_path=str(fake_pdf),
            course_id="course-202",
        )

    assert isinstance(result, MaterialSummary)
    assert len(result.topics) == 3

    for topic in result.topics:
        assert isinstance(topic, MaterialTopic)
        assert topic.title
        assert topic.description

    # First topic
    assert result.topics[0].title == "Topic 1: ML Basics"
    assert result.topics[0].source_range == "slides 1-3"
    # Second topic
    assert result.topics[1].description == "Deep dive into linear regression models and cost functions."
    assert result.topics[1].source_range == "slides 4-8"
    # Third topic
    assert result.topics[2].title == "Topic 3: Decision Trees"
    # Overall summary
    assert result.raw_summary == "Comprehensive ML overview covering basics, regression, and decision trees."
