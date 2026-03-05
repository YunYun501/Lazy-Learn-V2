import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import fitz
import pytest

from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser, detect_chapter_entries
from app.services.storage import MetadataStore

ROOT_DIR = Path(__file__).resolve().parents[2]
TEXTBOOK_PATH = ROOT_DIR / "Simulation Material" / "Textbook" / "DigitalControlSystems-NeweditionI.D.LandauG.Zito.pdf"


@pytest.fixture
async def storage(tmp_path):
    store = MetadataStore(db_path=tmp_path / "test.db")
    await store.initialize()
    return store


@pytest.fixture
def filesystem(tmp_path):
    fs = FilesystemManager(data_dir=tmp_path / "data")
    fs.initialize()
    return fs


def test_toc_extraction_on_real_textbook():
    doc = fitz.open(TEXTBOOK_PATH)
    parser = PDFParser.__new__(PDFParser)
    toc = parser.extract_toc(doc)
    doc.close()
    assert len(toc) >= 1
    for entry in toc:
        assert "level" in entry
        assert "title" in entry
        assert "page" in entry


def test_chapter_text_splitting():
    doc = fitz.open(TEXTBOOK_PATH)
    parser_obj = PDFParser.__new__(PDFParser)
    toc_entries = [
        {"level": 1, "title": "Introduction", "page": 1},
        {"level": 1, "title": "Chapter 2", "page": 20},
        {"level": 1, "title": "Chapter 3", "page": 44},
    ]
    chapters = parser_obj.split_into_chapters(doc, toc_entries)
    doc.close()

    assert len(chapters) == 3
    assert chapters[0].title == "Introduction"
    assert chapters[0].page_start == 1
    assert chapters[0].page_end == 19
    assert len(chapters[0].text) > 100


@pytest.mark.asyncio
async def test_ai_toc_fallback_called_when_no_bookmarks(storage, filesystem):
    mock_ai = AsyncMock()
    mock_ai.chat = AsyncMock(
        return_value='{"chapters": [{"number": "1", "title": "Introduction", "page": 1}]}'
    )

    parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=mock_ai)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path_str = f.name

    doc = fitz.open()
    doc.new_page()
    doc.save(tmp_path_str)
    doc.close()

    doc = fitz.open(tmp_path_str)
    toc = parser.extract_toc(doc)
    assert toc == []

    result = await parser.ai_toc_fallback(doc)
    doc.close()

    mock_ai.chat.assert_called_once()
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_parse_pdf_creates_chapter_files(storage, filesystem):
    parser = PDFParser(storage=storage, filesystem=filesystem)
    textbook_id = "test-textbook-001"

    result = await parser.parse_pdf(TEXTBOOK_PATH, textbook_id, "Digital Control Systems")

    assert len(result.chapters) > 0
    assert result.total_pages > 0

    chapter_dir = filesystem.textbooks_dir / textbook_id / "chapters"
    txt_files = list(chapter_dir.glob("*.txt"))
    assert len(txt_files) > 0

    chapters = await storage.list_chapters(textbook_id)
    assert len(chapters) > 0


# ── detect_chapter_entries tests ─────────────────────────────────────────


class TestDetectChapterEntries:
    """Tests for the TOC chapter-level detection logic."""

    def test_empty_toc_returns_empty(self):
        assert detect_chapter_entries([]) == []

    def test_simple_level1_only(self):
        """All chapters at level 1, no level 2 → return level 1."""
        toc = [
            {"level": 1, "title": "1 Introduction", "page": 1},
            {"level": 1, "title": "2 Methods", "page": 20},
            {"level": 1, "title": "3 Results", "page": 45},
        ]
        result = detect_chapter_entries(toc)
        assert len(result) == 3
        assert [e["title"] for e in result] == ["1 Introduction", "2 Methods", "3 Results"]

    def test_level1_chapters_with_level2_sections(self):
        """Level 1 = chapters, level 2 = dotted sub-sections → return level 1."""
        toc = [
            {"level": 1, "title": "1 Introduction", "page": 1},
            {"level": 2, "title": "1.1 Overview", "page": 1},
            {"level": 2, "title": "1.2 Background", "page": 5},
            {"level": 1, "title": "2 Methods", "page": 20},
            {"level": 2, "title": "2.1 Approach", "page": 20},
            {"level": 2, "title": "2.2 Data", "page": 30},
        ]
        result = detect_chapter_entries(toc)
        assert len(result) == 2
        assert [e["title"] for e in result] == ["1 Introduction", "2 Methods"]

    def test_part_chapter_structure(self):
        """Level 1 = Parts, level 2 = chapters → return level 2."""
        toc = [
            {"level": 1, "title": "Part I: Basics", "page": 1},
            {"level": 2, "title": "1 Introduction", "page": 1},
            {"level": 2, "title": "2 Fundamentals", "page": 20},
            {"level": 1, "title": "Part II: Advanced", "page": 50},
            {"level": 2, "title": "3 Complex Methods", "page": 50},
            {"level": 2, "title": "4 Applications", "page": 80},
        ]
        result = detect_chapter_entries(toc)
        assert len(result) == 4
        titles = [e["title"] for e in result]
        assert titles == ["1 Introduction", "2 Fundamentals", "3 Complex Methods", "4 Applications"]

    def test_mixed_structure_power_electronics_style(self):
        """Mixed: some chapters at level 1, others under Parts at level 2.
        Simulates the Power Electronics Handbook layout."""
        toc = [
            # Level-1 container (Part heading) with level-2 children
            {"level": 1, "title": "Contents", "page": 1},
            {"level": 1, "title": "Part I", "page": 5},
            {"level": 2, "title": "1 Introduction", "page": 5},
            {"level": 2, "title": "2 Power Diode", "page": 20},
            {"level": 2, "title": "3 Thyristors", "page": 35},
            # Standalone level-1 chapter (no children)
            {"level": 1, "title": "4 Gate Turn-Off Thyristors", "page": 55},
            # Another container
            {"level": 1, "title": "Part II", "page": 70},
            {"level": 2, "title": "5 Power MOSFETs", "page": 70},
            {"level": 2, "title": "6 IGBTs", "page": 90},
            {"level": 2, "title": "7 Power Transistors", "page": 110},
            # Another standalone
            {"level": 1, "title": "8 MOS Controlled Thyristors", "page": 130},
        ]
        result = detect_chapter_entries(toc)
        titles = [e["title"] for e in result]
        # Should include ALL chapters (1-8) but NOT Part headings or Contents
        assert "1 Introduction" in titles
        assert "2 Power Diode" in titles
        assert "3 Thyristors" in titles
        assert "4 Gate Turn-Off Thyristors" in titles
        assert "5 Power MOSFETs" in titles
        assert "6 IGBTs" in titles
        assert "7 Power Transistors" in titles
        assert "8 MOS Controlled Thyristors" in titles
        assert "Part I" not in titles
        assert "Part II" not in titles
        assert "Contents" not in titles
        assert len(result) == 8

    def test_meta_entries_filtered(self):
        """Meta entries like 'Preface' and 'Index' are stripped."""
        toc = [
            {"level": 1, "title": "Contents", "page": 1},
            {"level": 1, "title": "Preface", "page": 3},
            {"level": 1, "title": "Part I", "page": 5},
            {"level": 2, "title": "1 Introduction", "page": 5},
            {"level": 1, "title": "2 Methods", "page": 30},
            {"level": 1, "title": "Index", "page": 100},
        ]
        result = detect_chapter_entries(toc)
        titles = [e["title"] for e in result]
        assert "Contents" not in titles
        assert "Preface" not in titles
        assert "Index" not in titles
        assert "1 Introduction" in titles
        assert "2 Methods" in titles

    def test_only_level2_entries(self):
        """No level-1 entries → return level 2."""
        toc = [
            {"level": 2, "title": "1 Intro", "page": 1},
            {"level": 2, "title": "2 Body", "page": 10},
        ]
        result = detect_chapter_entries(toc)
        assert len(result) == 2

    def test_chapters_sorted_by_page(self):
        """Returned chapter entries are sorted by page number."""
        toc = [
            {"level": 1, "title": "Part II", "page": 50},
            {"level": 2, "title": "3 Later", "page": 50},
            {"level": 1, "title": "Part I", "page": 1},
            {"level": 2, "title": "1 First", "page": 1},
            {"level": 2, "title": "2 Second", "page": 25},
        ]
        result = detect_chapter_entries(toc)
        pages = [e["page"] for e in result]
        assert pages == sorted(pages)

    def test_page_zero_fixup(self):
        """Entries with page=0 get their page inferred from the next valid entry."""
        toc = [
            {"level": 1, "title": "1 Introduction", "page": 17},
            {"level": 2, "title": "1.1 Overview", "page": 17},
            {"level": 1, "title": "2 Methods", "page": 0},  # broken bookmark
            {"level": 2, "title": "2.1 Approach", "page": 45},
            {"level": 1, "title": "3 Results", "page": 80},
            {"level": 2, "title": "3.1 Findings", "page": 80},
        ]
        result = detect_chapter_entries(toc)
        assert len(result) == 3
        pages = [e["page"] for e in result]
        # Chapter 2 should have page=45 (from first child 2.1)
        assert pages == [17, 45, 80]
        assert result[1]["title"] == "2 Methods"

    def test_meta_filtered_in_simple_level1_case(self):
        """Meta entries are filtered even when all chapters are at level 1 with sections at level 2."""
        toc = [
            {"level": 1, "title": "Contents", "page": 5},
            {"level": 1, "title": "Preface", "page": 11},
            {"level": 2, "title": "Introduction", "page": 11},
            {"level": 2, "title": "Acknowledgments", "page": 12},
            {"level": 1, "title": "List of Contributors", "page": 13},
            {"level": 1, "title": "1 Introduction", "page": 17},
            {"level": 2, "title": "1.1 Overview", "page": 17},
            {"level": 2, "title": "1.2 Background", "page": 20},
            {"level": 1, "title": "2 The Power Diode", "page": 30},
            {"level": 2, "title": "2.1 Diode as Switch", "page": 30},
        ]
        result = detect_chapter_entries(toc)
        titles = [e["title"] for e in result]
        assert "Contents" not in titles
        assert "Preface" not in titles
        assert "List of Contributors" not in titles
        assert "1 Introduction" in titles
        assert "2 The Power Diode" in titles
        assert len(result) == 2

    def test_real_power_electronics_structure(self):
        """Reproduces the actual Power Electronics Handbook TOC structure.
        Level 1 = chapters (some with page=0), Level 2 = dotted sections.
        Meta entries at level 1. No Part headings."""
        toc = [
            {"level": 1, "title": "Contents", "page": 5},
            {"level": 1, "title": "Preface", "page": 11},
            {"level": 2, "title": "Introduction", "page": 11},
            {"level": 2, "title": "Acknowledgments", "page": 12},
            {"level": 1, "title": "List of Contributors", "page": 13},
            {"level": 1, "title": "1 Introduction", "page": 17},
            {"level": 2, "title": "1.1 Power Electronics Defined", "page": 17},
            {"level": 2, "title": "1.2 Key Characteristics", "page": 18},
            {"level": 1, "title": "2 The Power Diode", "page": 30},
            {"level": 2, "title": "2.1 Diode as a Switch", "page": 30},
            {"level": 1, "title": "3 Thyristors", "page": 41},
            {"level": 2, "title": "3.1 Introduction", "page": 41},
            # Chapter with page=0 — broken bookmark
            {"level": 1, "title": "4 Gate Turn-Off Thyristors", "page": 0},
            {"level": 2, "title": "4.1 Introduction", "page": 69},
            {"level": 1, "title": "5 Power Bipolar Transistors", "page": 76},
            {"level": 2, "title": "5.1 Introduction", "page": 76},
            # Another page=0 chapter
            {"level": 1, "title": "6 The Power MOSFET", "page": 0},
            {"level": 2, "title": "6.1 Introduction", "page": 88},
        ]
        result = detect_chapter_entries(toc)
        titles = [e["title"] for e in result]
        pages = [e["page"] for e in result]

        # Meta entries filtered
        assert "Contents" not in titles
        assert "Preface" not in titles
        assert "List of Contributors" not in titles

        # All 6 chapters present, in page order
        assert len(result) == 6
        assert titles == [
            "1 Introduction",
            "2 The Power Diode",
            "3 Thyristors",
            "4 Gate Turn-Off Thyristors",
            "5 Power Bipolar Transistors",
            "6 The Power MOSFET",
        ]

        # Page 0 entries were fixed
        assert 0 not in pages
        assert pages == [17, 30, 41, 69, 76, 88]
