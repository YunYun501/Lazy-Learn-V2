"""Tests for the Material Organizer service (Task 25)."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.material_organizer import (
    CATEGORY_FOLDER_MAP,
    CLASSIFY_SYSTEM_PROMPT,
    MaterialOrganizer,
    OrganizationResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_classification_response(
    category: str = "lecture_slides",
    course_code: str | None = "EE2010",
    title: str | None = "Lecture 1",
    date: str | None = "2024",
) -> str:
    """Return a valid JSON string mimicking a DeepSeek classification response."""
    return json.dumps(
        {
            "category": category,
            "course_code": course_code,
            "title": title,
            "date": date,
        }
    )


def _make_organizer(mock_ai_return: str | list[str]) -> MaterialOrganizer:
    """Create a MaterialOrganizer with a mocked AI provider and no document parser."""
    provider = MagicMock()
    if isinstance(mock_ai_return, list):
        provider.chat = AsyncMock(side_effect=mock_ai_return)
    else:
        provider.chat = AsyncMock(return_value=mock_ai_return)

    # Use a minimal document parser mock that returns an empty ParsedDocument
    parser = MagicMock()
    parsed_doc = MagicMock()
    parsed_doc.chapters = []
    parsed_doc.total_pages = 0
    parser.parse = MagicMock(return_value=parsed_doc)

    return MaterialOrganizer(ai_provider=provider, document_parser=parser)


def _create_fake_pdf(directory: Path, filename: str = "lecture1.pdf") -> Path:
    """Create a minimal (fake) PDF file for testing — no real PDF content needed."""
    file_path = directory / filename
    # Write fake bytes — the AI call will be mocked so content doesn't matter
    file_path.write_bytes(b"%PDF-1.4 fake content")
    return file_path


# ---------------------------------------------------------------------------
# Test 1: Lecture PDF is classified as lecture_slides → copied to lectures/
# ---------------------------------------------------------------------------


async def test_lecture_pdf_classified_and_copied_to_lectures(tmp_path: Path):
    """A PDF classified as lecture_slides must be copied into dest/lectures/."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()

    pdf_file = _create_fake_pdf(source_dir, "lecture1.pdf")

    organizer = _make_organizer(_make_classification_response(category="lecture_slides"))

    result = await organizer.organize_materials(str(source_dir), str(dest_dir))

    # One file found and organized
    assert result.total_found == 1
    assert result.total_organized == 1
    assert result.total_skipped == 0

    # Organized file has correct category
    assert len(result.organized_files) == 1
    organized = result.organized_files[0]
    assert organized.category == "lecture_slides"

    # File was copied to the lectures/ subdirectory
    expected_dest = dest_dir / "lectures" / "lecture1.pdf"
    assert expected_dest.exists(), f"Expected {expected_dest} to exist after organizing"

    # Original file is still present (COPY not move)
    assert pdf_file.exists(), "Original file must NOT be moved — only copied"

    # A .md description was created alongside the copied file
    expected_md = dest_dir / "lectures" / "lecture1.md"
    assert expected_md.exists(), "Expected .md description file to be created"


# ---------------------------------------------------------------------------
# Test 2: Duplicate file is skipped (not copied twice)
# ---------------------------------------------------------------------------


async def test_duplicate_file_is_skipped(tmp_path: Path):
    """When the target filename already exists in dest_dir, the file must be skipped."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()

    pdf_file = _create_fake_pdf(source_dir, "exam.pdf")

    # Pre-populate the destination with the same filename
    lectures_dir = dest_dir / "past_exam_papers"  # wrong folder on purpose
    exams_dir = dest_dir / "exams"
    exams_dir.mkdir(parents=True)
    (exams_dir / "exam.pdf").write_bytes(b"already here")

    organizer = _make_organizer(_make_classification_response(category="past_exam_papers"))

    result = await organizer.organize_materials(str(source_dir), str(dest_dir))

    assert result.total_found == 1
    assert result.total_skipped == 1
    assert result.total_organized == 0
    assert len(result.organized_files) == 0
    assert len(result.skipped_files) == 1
    assert str(pdf_file) in result.skipped_files[0]


# ---------------------------------------------------------------------------
# Test 3: OrganizationResult contains correct file count and categories
# ---------------------------------------------------------------------------


async def test_organization_result_counts_and_categories(tmp_path: Path):
    """organize_materials() must correctly count files and group by category."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()

    # Create 3 fake PDF files
    _create_fake_pdf(source_dir, "lecture_week1.pdf")
    _create_fake_pdf(source_dir, "lecture_week2.pdf")
    _create_fake_pdf(source_dir, "tutorial1.pdf")

    # AI responds: first two → lecture_slides, third → tutorial_questions
    responses = [
        _make_classification_response(category="lecture_slides", title="Week 1 Lecture"),
        _make_classification_response(category="lecture_slides", title="Week 2 Lecture"),
        _make_classification_response(category="tutorial_questions", title="Tutorial 1"),
    ]
    organizer = _make_organizer(responses)

    result = await organizer.organize_materials(str(source_dir), str(dest_dir))

    assert result.total_found == 3
    assert result.total_organized == 3
    assert result.total_skipped == 0

    # Check category counts
    categories = result.categories
    assert categories.get("lecture_slides") == 2
    assert categories.get("tutorial_questions") == 1

    # Verify folder structure
    assert (dest_dir / "lectures").is_dir()
    assert (dest_dir / "tutorials").is_dir()
    assert len(list((dest_dir / "lectures").glob("*.pdf"))) == 2
    assert len(list((dest_dir / "tutorials").glob("*.pdf"))) == 1


# ---------------------------------------------------------------------------
# Test 4: Unknown AI category falls back to 'other'
# ---------------------------------------------------------------------------


async def test_invalid_category_falls_back_to_other(tmp_path: Path):
    """When DeepSeek returns an unrecognised category, the file goes to other/."""
    source_dir = tmp_path / "source"
    dest_dir = tmp_path / "dest"
    source_dir.mkdir()

    _create_fake_pdf(source_dir, "unknown_doc.pdf")

    # AI returns a category not in CATEGORY_FOLDER_MAP
    organizer = _make_organizer(
        json.dumps({"category": "totally_unknown", "course_code": None, "title": None, "date": None})
    )

    result = await organizer.organize_materials(str(source_dir), str(dest_dir))

    assert result.total_organized == 1
    organized = result.organized_files[0]
    assert organized.category == "other"
    assert (dest_dir / "other" / "unknown_doc.pdf").exists()


# ---------------------------------------------------------------------------
# Test 5: CLASSIFY_SYSTEM_PROMPT contains required classification categories
# ---------------------------------------------------------------------------


def test_classify_system_prompt_contains_all_categories():
    """CLASSIFY_SYSTEM_PROMPT must reference all 7 required document categories."""
    required_categories = [
        "lecture_slides",
        "tutorial_questions",
        "tutorial_solutions",
        "past_exam_papers",
        "lab_manual",
        "reference_notes",
        "other",
    ]
    for cat in required_categories:
        assert cat in CLASSIFY_SYSTEM_PROMPT, (
            f"CLASSIFY_SYSTEM_PROMPT missing required category: {cat}"
        )

    # Must also specify JSON output format
    assert "category" in CLASSIFY_SYSTEM_PROMPT
    assert "course_code" in CLASSIFY_SYSTEM_PROMPT
    assert "title" in CLASSIFY_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Test 6: CATEGORY_FOLDER_MAP covers all expected categories
# ---------------------------------------------------------------------------


def test_category_folder_map_is_complete():
    """CATEGORY_FOLDER_MAP must have a folder entry for all 7 categories."""
    expected = {
        "lecture_slides",
        "tutorial_questions",
        "tutorial_solutions",
        "past_exam_papers",
        "lab_manual",
        "reference_notes",
        "other",
    }
    assert set(CATEGORY_FOLDER_MAP.keys()) == expected
    # Spot-check key mappings
    assert CATEGORY_FOLDER_MAP["lecture_slides"] == "lectures"
    assert CATEGORY_FOLDER_MAP["tutorial_solutions"] == "tutorials/solutions"
    assert CATEGORY_FOLDER_MAP["past_exam_papers"] == "exams"
