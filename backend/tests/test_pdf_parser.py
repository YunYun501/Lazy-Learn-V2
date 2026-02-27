import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import fitz
import pytest

from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser
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
