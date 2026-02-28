import pytest
from pydantic import ValidationError
from app.models.pipeline_models import (
    PipelineStatus,
    ExtractionStatus,
    ContentType,
    Section,
    ExtractedContent,
    MaterialTopic,
    MaterialSummary,
    RelevanceResult,
    ChapterVerificationRequest,
    ChapterWithStatus,
)


def test_section_model_validation():
    """Test Section model validation: valid creation and required field enforcement."""
    # Valid Section
    section = Section(
        id="sec-1",
        chapter_id="ch-1",
        section_number=1,
        title="Introduction",
        page_start=10,
        page_end=15,
    )
    assert section.id == "sec-1"
    assert section.chapter_id == "ch-1"
    assert section.section_number == 1
    assert section.title == "Introduction"
    assert section.page_start == 10
    assert section.page_end == 15

    # Missing required field should raise ValidationError
    with pytest.raises(ValidationError):
        Section(
            id="sec-2",
            chapter_id="ch-1",
            section_number=2,
            title="Missing page_start",
            page_end=20,
        )


def test_extracted_content_model():
    """Test ExtractedContent model for each ContentType enum value."""
    content_types = [
        ContentType.table,
        ContentType.figure,
        ContentType.equation,
        ContentType.text,
    ]

    for content_type in content_types:
        content = ExtractedContent(
            id=f"content-{content_type.value}",
            chapter_id="ch-1",
            content_type=content_type,
            title=f"Sample {content_type.value}",
            content="Sample content",
            file_path="/path/to/file",
            page_number=5,
            order_index=0,
        )
        assert content.content_type == content_type
        assert content.id == f"content-{content_type.value}"


def test_material_summary_model():
    """Test MaterialSummary model with multiple MaterialTopic items."""
    topics = [
        MaterialTopic(
            title="Topic 1",
            description="Description 1",
            source_range="slides 1-5",
        ),
        MaterialTopic(
            title="Topic 2",
            description="Description 2",
            source_range="slides 6-10",
        ),
        MaterialTopic(
            title="Topic 3",
            description="Description 3",
        ),
    ]

    summary = MaterialSummary(
        id="summary-1",
        material_id="mat-1",
        course_id="course-1",
        topics=topics,
        raw_summary="Raw summary text",
        created_at="2026-02-28T10:00:00Z",
    )

    assert len(summary.topics) == 3
    assert summary.topics[0].title == "Topic 1"
    assert summary.topics[1].source_range == "slides 6-10"
    assert summary.topics[2].source_range is None


def test_pipeline_status_enum():
    """Test PipelineStatus enum: all 7 values accessible."""
    statuses = [
        PipelineStatus.uploaded,
        PipelineStatus.toc_extracted,
        PipelineStatus.awaiting_verification,
        PipelineStatus.extracting,
        PipelineStatus.partially_extracted,
        PipelineStatus.fully_extracted,
        PipelineStatus.error,
    ]
    assert len(statuses) == 7
    assert PipelineStatus.uploaded.value == "uploaded"
    assert PipelineStatus.error.value == "error"


def test_chapter_extraction_status_enum():
    """Test ExtractionStatus enum: all 6 values accessible."""
    statuses = [
        ExtractionStatus.pending,
        ExtractionStatus.selected,
        ExtractionStatus.extracting,
        ExtractionStatus.extracted,
        ExtractionStatus.deferred,
        ExtractionStatus.error,
    ]
    assert len(statuses) == 6
    assert ExtractionStatus.pending.value == "pending"
    assert ExtractionStatus.error.value == "error"


def test_relevance_result_model():
    """Test RelevanceResult model with score and matched_topics."""
    result = RelevanceResult(
        chapter_id="ch-1",
        chapter_title="Chapter 1: Basics",
        relevance_score=0.8,
        matched_topics=["topic1", "topic2"],
        reasoning="Matches course material well",
    )

    assert result.chapter_id == "ch-1"
    assert result.relevance_score == 0.8
    assert len(result.matched_topics) == 2
    assert result.matched_topics[0] == "topic1"
    assert result.reasoning == "Matches course material well"
