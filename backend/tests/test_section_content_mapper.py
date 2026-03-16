"""Tests for section_content_mapper.py — TDD first."""

import pytest
import aiosqlite
from pathlib import Path
from app.services.storage import MetadataStore
from app.services.section_content_mapper import (
    map_content_to_sections,
    compute_section_path,
    get_sections_with_content,
)


@pytest.fixture
async def store_with_data(tmp_path):
    """Store with chapter 7 (pages 1-100), two sections, and content entries."""
    s = MetadataStore(tmp_path / "test.db")
    await s.initialize()
    tb_id = await s.create_textbook("Test Book", "t.pdf")
    ch_id = await s.create_chapter(tb_id, "7", "Chapter 7", 1, 100)

    # Section 1: pages 1-30
    sec1_id = await s.create_section(
        {
            "chapter_id": ch_id,
            "section_number": 1,
            "title": "Introduction",
            "page_start": 1,
            "page_end": 30,
            "parent_section_id": None,
            "level": 2,
        }
    )

    # Section 2: pages 31-60
    sec2_id = await s.create_section(
        {
            "chapter_id": ch_id,
            "section_number": 2,
            "title": "Main Content",
            "page_start": 31,
            "page_end": 60,
            "parent_section_id": None,
            "level": 2,
        }
    )

    # Section 3: pages 61-100
    sec3_id = await s.create_section(
        {
            "chapter_id": ch_id,
            "section_number": 3,
            "title": "Conclusion",
            "page_start": 61,
            "page_end": 100,
            "parent_section_id": None,
            "level": 2,
        }
    )

    return s, ch_id, sec1_id, sec2_id, sec3_id


@pytest.fixture
async def store_with_hierarchy(tmp_path):
    """Store with parent/child section hierarchy for path tests."""
    s = MetadataStore(tmp_path / "test.db")
    await s.initialize()
    tb_id = await s.create_textbook("Test Book", "t.pdf")
    ch_id = await s.create_chapter(tb_id, "7", "Chapter 7", 1, 100)

    # Root section (no parent)
    root_id = await s.create_section(
        {
            "chapter_id": ch_id,
            "section_number": 1,
            "title": "Root Section",
            "page_start": 1,
            "page_end": 50,
            "parent_section_id": None,
            "level": 2,
        }
    )

    # Child section
    child_id = await s.create_section(
        {
            "chapter_id": ch_id,
            "section_number": 2,
            "title": "Child Section",
            "page_start": 10,
            "page_end": 30,
            "parent_section_id": root_id,
            "level": 3,
        }
    )

    return s, ch_id, root_id, child_id


# ─── Test 1: content maps to correct section by page range ───────────────────


@pytest.mark.asyncio
async def test_content_maps_to_correct_section(store_with_data):
    s, ch_id, sec1_id, sec2_id, sec3_id = store_with_data

    # Content on page 15 → should map to sec1 (pages 1-30)
    await s.create_extracted_content(
        {
            "chapter_id": ch_id,
            "content_type": "text",
            "title": "Intro text",
            "content": "Hello world",
            "page_number": 15,
            "order_index": 0,
        }
    )

    result = await map_content_to_sections(s, ch_id)

    assert sec1_id in result
    assert len(result[sec1_id]) == 1
    assert result[sec1_id][0]["page_number"] == 15
    # sec2 and sec3 should not have content (or be absent)
    assert sec2_id not in result or len(result[sec2_id]) == 0


# ─── Test 2: null page_number maps to first section ──────────────────────────


@pytest.mark.asyncio
async def test_null_page_number_maps_to_first_section(store_with_data):
    s, ch_id, sec1_id, sec2_id, sec3_id = store_with_data

    await s.create_extracted_content(
        {
            "chapter_id": ch_id,
            "content_type": "image",
            "title": "Unknown page image",
            "content": None,
            "page_number": None,
            "order_index": 0,
        }
    )

    result = await map_content_to_sections(s, ch_id)

    # Should be assigned to first section (sec1, page_start=1)
    assert sec1_id in result
    assert len(result[sec1_id]) == 1
    assert result[sec1_id][0]["page_number"] is None


# ─── Test 3: orphan content maps to nearest section ──────────────────────────


@pytest.mark.asyncio
async def test_orphan_content_maps_to_nearest_section(store_with_data):
    s, ch_id, sec1_id, sec2_id, sec3_id = store_with_data

    # Page 200 is outside all sections (max page_end=100)
    # Nearest section by distance to page_start: sec3 (page_start=61, dist=139)
    # vs sec2 (page_start=31, dist=169) vs sec1 (page_start=1, dist=199)
    # → sec3 is nearest
    await s.create_extracted_content(
        {
            "chapter_id": ch_id,
            "content_type": "text",
            "title": "Orphan content",
            "content": "Far away",
            "page_number": 200,
            "order_index": 0,
        }
    )

    result = await map_content_to_sections(s, ch_id)

    assert sec3_id in result
    assert len(result[sec3_id]) == 1
    assert result[sec3_id][0]["page_number"] == 200


# ─── Test 4: section_path for root section ───────────────────────────────────


@pytest.mark.asyncio
async def test_section_path_root(store_with_hierarchy):
    s, ch_id, root_id, child_id = store_with_hierarchy

    path = await compute_section_path(s, root_id, "7")

    assert path == "CH7/1"


# ─── Test 5: section_path for child section ──────────────────────────────────


@pytest.mark.asyncio
async def test_section_path_child(store_with_hierarchy):
    s, ch_id, root_id, child_id = store_with_hierarchy

    path = await compute_section_path(s, child_id, "7")

    assert path == "CH7/1/2"


# ─── Test 6: get_sections_with_content returns only sections with content ────


@pytest.mark.asyncio
async def test_get_sections_with_content(store_with_data):
    s, ch_id, sec1_id, sec2_id, sec3_id = store_with_data

    # Add content only to sec1 (page 15) and sec3 (page 80)
    await s.create_extracted_content(
        {
            "chapter_id": ch_id,
            "content_type": "text",
            "title": "Intro text",
            "content": "Hello",
            "page_number": 15,
            "order_index": 0,
        }
    )
    await s.create_extracted_content(
        {
            "chapter_id": ch_id,
            "content_type": "text",
            "title": "Conclusion text",
            "content": "Bye",
            "page_number": 80,
            "order_index": 1,
        }
    )

    sections = await get_sections_with_content(s, ch_id)

    section_ids = [sec["id"] for sec in sections]
    assert sec1_id in section_ids
    assert sec3_id in section_ids
    # sec2 has no content → should NOT be in results
    assert sec2_id not in section_ids

    # Each section dict should have content_entries and section_path
    for sec in sections:
        assert "content_entries" in sec
        assert "section_path" in sec
        assert len(sec["content_entries"]) > 0


# ─── Test 7: multiple content entries in same section ────────────────────────


@pytest.mark.asyncio
async def test_multiple_content_in_same_section(store_with_data):
    s, ch_id, sec1_id, sec2_id, sec3_id = store_with_data

    # Three entries all in sec2 (pages 31-60)
    for i, page in enumerate([35, 40, 55]):
        await s.create_extracted_content(
            {
                "chapter_id": ch_id,
                "content_type": "text",
                "title": f"Content {i}",
                "content": f"Text {i}",
                "page_number": page,
                "order_index": i,
            }
        )

    result = await map_content_to_sections(s, ch_id)

    assert sec2_id in result
    assert len(result[sec2_id]) == 3


# ─── Test 8: empty chapter returns empty mapping ─────────────────────────────


@pytest.mark.asyncio
async def test_empty_chapter_returns_empty_mapping(tmp_path):
    s = MetadataStore(tmp_path / "empty.db")
    await s.initialize()
    tb_id = await s.create_textbook("Empty Book", "e.pdf")
    ch_id = await s.create_chapter(tb_id, "1", "Chapter 1", 1, 50)

    result = await map_content_to_sections(s, ch_id)

    assert result == {}
