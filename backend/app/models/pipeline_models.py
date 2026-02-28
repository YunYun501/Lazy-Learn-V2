from enum import Enum
from pydantic import BaseModel
from typing import Optional


class PipelineStatus(str, Enum):
    """Pipeline processing status for textbooks."""
    uploaded = "uploaded"
    toc_extracted = "toc_extracted"
    awaiting_verification = "awaiting_verification"
    extracting = "extracting"
    partially_extracted = "partially_extracted"
    fully_extracted = "fully_extracted"
    error = "error"


class ExtractionStatus(str, Enum):
    """Chapter extraction status within a pipeline."""
    pending = "pending"
    selected = "selected"
    extracting = "extracting"
    extracted = "extracted"
    deferred = "deferred"
    error = "error"


class ContentType(str, Enum):
    """Type of extracted content."""
    table = "table"
    figure = "figure"
    equation = "equation"
    text = "text"


class Section(BaseModel):
    """A section within a chapter."""
    id: str
    chapter_id: str
    section_number: int
    title: str
    page_start: int
    page_end: int


class ExtractedContent(BaseModel):
    """Extracted content from a chapter."""
    id: str
    chapter_id: str
    content_type: ContentType
    title: Optional[str] = None
    content: Optional[str] = None
    file_path: Optional[str] = None
    page_number: Optional[int] = None
    order_index: int = 0


class MaterialTopic(BaseModel):
    """A topic within a material summary."""
    title: str
    description: str
    source_range: Optional[str] = None  # e.g., "slides 1-5"


class MaterialSummary(BaseModel):
    """Summary of a material document with extracted topics."""
    id: str
    material_id: str
    course_id: str
    topics: list[MaterialTopic]
    raw_summary: Optional[str] = None
    created_at: Optional[str] = None


class RelevanceResult(BaseModel):
    """Relevance matching result for a chapter."""
    chapter_id: str
    chapter_title: str
    relevance_score: float  # 0.0-1.0
    matched_topics: list[str]
    reasoning: Optional[str] = None


class ChapterVerificationRequest(BaseModel):
    """Request to verify and select chapters for extraction."""
    selected_chapter_ids: list[str]


class ChapterWithStatus(BaseModel):
    """Chapter with its extraction and relevance status."""
    id: str
    title: str
    chapter_number: int
    page_start: int
    page_end: int
    extraction_status: ExtractionStatus = ExtractionStatus.pending
    relevance_score: Optional[float] = None
    matched_topics: Optional[list[str]] = None
