"""Tests for the flattened/scanned PDF → MinerU OCR → AI TOC pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest

from app.services.filesystem import FilesystemManager
from app.services.pdf_parser import PDFParser
from app.services.storage import MetadataStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_blank_pdf(path: Path, pages: int = 5) -> Path:
    """Create a blank (no text) PDF to simulate a scanned document."""
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(str(path))
    doc.close()
    return path


def _create_text_pdf(path: Path, pages: int = 5) -> Path:
    """Create a PDF with embedded text on every page."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"This is page {i + 1} with enough text to exceed the threshold. " * 10)
    doc.save(str(path))
    doc.close()
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# FilesystemManager.mineru_cache_path
# ---------------------------------------------------------------------------


class TestMineruCachePath:
    def test_returns_path_under_textbook_dir(self, filesystem):
        path = filesystem.mineru_cache_path("tb-001")
        assert path.name == "pages.json"
        assert "mineru_cache" in str(path)
        assert "tb-001" in str(path)

    def test_creates_cache_directory(self, filesystem):
        path = filesystem.mineru_cache_path("tb-002")
        assert path.parent.exists()
        assert path.parent.name == "mineru_cache"

    def test_write_and_read_cache(self, filesystem):
        path = filesystem.mineru_cache_path("tb-003")
        data = {"1": "page one text", "2": "page two text"}
        path.write_text(json.dumps(data), encoding="utf-8")
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == data


# ---------------------------------------------------------------------------
# PDFParser.ai_toc_from_text
# ---------------------------------------------------------------------------


class TestAiTocFromText:
    @pytest.mark.asyncio
    async def test_returns_toc_entries_from_ai_response(self, storage, filesystem):
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "toc_entries": [
                {"level": 1, "title": "Part I", "page": 1},
                {"level": 2, "title": "1 Introduction", "page": 1},
                {"level": 2, "title": "2 Methods", "page": 15},
            ]
        }))
        parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=mock_ai)

        result = await parser.ai_toc_from_text("--- Page 1 ---\nSome OCR text")
        assert len(result) == 3
        assert result[0]["title"] == "Part I"
        assert result[1]["level"] == 2
        assert result[2]["page"] == 15
        mock_ai.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_supports_legacy_chapters_format(self, storage, filesystem):
        """Handles AI responses using 'chapters' key instead of 'toc_entries'."""
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "chapters": [
                {"number": "1", "title": "Introduction", "page": 1},
                {"number": "2", "title": "Analysis", "page": 20},
            ]
        }))
        parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=mock_ai)

        result = await parser.ai_toc_from_text("Some text")
        assert len(result) == 2
        assert result[0]["title"] == "Introduction"

    @pytest.mark.asyncio
    async def test_returns_full_document_when_no_provider(self, storage, filesystem):
        parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=None)
        result = await parser.ai_toc_from_text("Some text")
        assert len(result) == 1
        assert result[0]["title"] == "Full Document"

    @pytest.mark.asyncio
    async def test_returns_full_document_on_ai_error(self, storage, filesystem):
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(side_effect=Exception("API error"))
        parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=mock_ai)

        result = await parser.ai_toc_from_text("Some text")
        assert len(result) == 1
        assert result[0]["title"] == "Full Document"


# ---------------------------------------------------------------------------
# PDFParser.ai_toc_fallback delegates to ai_toc_from_text
# ---------------------------------------------------------------------------


class TestAiTocFallbackDelegation:
    @pytest.mark.asyncio
    async def test_fallback_delegates_to_ai_toc_from_text(self, storage, filesystem):
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "toc_entries": [
                {"level": 1, "title": "1 Chapter One", "page": 1},
            ]
        }))
        parser = PDFParser(storage=storage, filesystem=filesystem, ai_provider=mock_ai)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmp_path = f.name
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello world " * 50)
        doc.save(tmp_path)
        doc.close()

        doc = fitz.open(tmp_path)
        result = await parser.ai_toc_fallback(doc)
        doc.close()

        assert len(result) >= 1
        assert result[0]["title"] == "1 Chapter One"
        mock_ai.chat.assert_called_once()


# ---------------------------------------------------------------------------
# TocExtractionService — flattened pipeline
# ---------------------------------------------------------------------------


class TestTocExtractionServiceFlattened:
    """Tests for TocExtractionService with flattened/scanned PDF detection."""

    @pytest.mark.asyncio
    async def test_flattened_pdf_uses_mineru_pipeline(self, tmp_path, storage, filesystem):
        """When PDF is flattened and MinerU is available, use MinerU OCR → AI TOC."""
        from app.routers.textbooks import TocExtractionService

        # Create a blank PDF (no text = flattened)
        pdf_path = _create_blank_pdf(tmp_path / "scanned.pdf", pages=35)

        # Register textbook in DB
        textbook_id = "tb-flattened-001"
        await storage.create_textbook(
            textbook_id=textbook_id,
            title="Scanned Textbook",
            filepath=str(pdf_path),
        )

        # Mock MinerU extractor
        mock_mineru = MagicMock()
        mock_mineru.is_available.return_value = True
        mock_mineru.extract_text_by_pages.return_value = {
            1: "Table of Contents\nChapter 1: Intro ........ 1\nChapter 2: Methods ........ 15",
            2: "Chapter 3: Results ........ 30\nChapter 4: Discussion ........ 45",
        }

        # Mock AI provider
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "toc_entries": [
                {"level": 1, "title": "Chapter 1: Intro", "page": 1},
                {"level": 1, "title": "Chapter 2: Methods", "page": 15},
                {"level": 1, "title": "Chapter 3: Results", "page": 30},
                {"level": 1, "title": "Chapter 4: Discussion", "page": 45},
            ]
        }))

        service = TocExtractionService(
            store=storage, filesystem=filesystem,
            ai_provider=mock_ai, mineru_extractor=mock_mineru,
        )
        result = await service.extract_toc(textbook_id)

        # MinerU was called with first 30 pages
        mock_mineru.extract_text_by_pages.assert_called_once()
        call_kwargs = mock_mineru.extract_text_by_pages.call_args
        assert call_kwargs.kwargs.get("start_page_id") == 0
        assert call_kwargs.kwargs.get("end_page_id") == 29

        # AI was called
        mock_ai.chat.assert_called_once()

        # Result has 4 chapters
        assert len(result["chapters"]) == 4
        assert result["chapters"][0]["title"] == "Chapter 1: Intro"

        # MinerU pages were cached
        cache_path = filesystem.mineru_cache_path(textbook_id)
        assert cache_path.exists()
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        assert "1" in cached
        assert "2" in cached

    @pytest.mark.asyncio
    async def test_text_pdf_uses_ai_fallback_not_mineru(self, tmp_path, storage, filesystem):
        """When PDF has embedded text, use AI fallback instead of MinerU."""
        from app.routers.textbooks import TocExtractionService

        # Create a PDF with text (not flattened)
        pdf_path = _create_text_pdf(tmp_path / "text.pdf", pages=5)

        textbook_id = "tb-text-001"
        await storage.create_textbook(
            textbook_id=textbook_id,
            title="Normal Textbook",
            filepath=str(pdf_path),
        )

        # Mock MinerU extractor (should NOT be called)
        mock_mineru = MagicMock()
        mock_mineru.is_available.return_value = True

        # Mock AI provider
        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "toc_entries": [
                {"level": 1, "title": "1 Introduction", "page": 1},
            ]
        }))

        service = TocExtractionService(
            store=storage, filesystem=filesystem,
            ai_provider=mock_ai, mineru_extractor=mock_mineru,
        )
        result = await service.extract_toc(textbook_id)

        # MinerU should NOT have been called (PDF has embedded text)
        mock_mineru.extract_text_by_pages.assert_not_called()

        # AI fallback was used
        mock_ai.chat.assert_called_once()
        assert len(result["chapters"]) >= 1

    @pytest.mark.asyncio
    async def test_bookmarks_short_circuit_skips_mineru_and_ai(self, tmp_path, storage, filesystem):
        """When PDF has bookmarks, neither MinerU nor AI should be called."""
        from app.routers.textbooks import TocExtractionService

        # Create a PDF with bookmarks
        pdf_path = tmp_path / "bookmarked.pdf"
        doc = fitz.open()
        for i in range(5):
            doc.new_page()
        toc = [
            [1, "Chapter 1", 1],
            [1, "Chapter 2", 3],
        ]
        doc.set_toc(toc)
        doc.save(str(pdf_path))
        doc.close()

        textbook_id = "tb-bookmarked-001"
        await storage.create_textbook(
            textbook_id=textbook_id,
            title="Bookmarked Textbook",
            filepath=str(pdf_path),
        )

        mock_mineru = MagicMock()
        mock_mineru.is_available.return_value = True
        mock_ai = AsyncMock()

        service = TocExtractionService(
            store=storage, filesystem=filesystem,
            ai_provider=mock_ai, mineru_extractor=mock_mineru,
        )
        result = await service.extract_toc(textbook_id)

        # Neither MinerU nor AI was called
        mock_mineru.extract_text_by_pages.assert_not_called()
        mock_ai.chat.assert_not_called()

        # Chapters from bookmarks
        assert len(result["chapters"]) == 2
        assert result["chapters"][0]["title"] == "Chapter 1"

    @pytest.mark.asyncio
    async def test_flattened_without_mineru_falls_back_to_ai(self, tmp_path, storage, filesystem):
        """When PDF is flattened but MinerU unavailable, use AI fallback."""
        from app.routers.textbooks import TocExtractionService

        pdf_path = _create_blank_pdf(tmp_path / "scanned_no_mineru.pdf", pages=5)

        textbook_id = "tb-no-mineru-001"
        await storage.create_textbook(
            textbook_id=textbook_id,
            title="Scanned No MinerU",
            filepath=str(pdf_path),
        )

        # MinerU not available
        mock_mineru = MagicMock()
        mock_mineru.is_available.return_value = False

        mock_ai = AsyncMock()
        mock_ai.chat = AsyncMock(return_value=json.dumps({
            "toc_entries": [{"level": 1, "title": "Full Document", "page": 1}]
        }))

        service = TocExtractionService(
            store=storage, filesystem=filesystem,
            ai_provider=mock_ai, mineru_extractor=mock_mineru,
        )
        result = await service.extract_toc(textbook_id)

        # MinerU not called (unavailable)
        mock_mineru.extract_text_by_pages.assert_not_called()

        # AI fallback was used
        mock_ai.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_mineru_returns_empty_falls_back(self, tmp_path, storage, filesystem):
        """When MinerU returns empty pages, fall back to Full Document."""
        from app.routers.textbooks import TocExtractionService

        pdf_path = _create_blank_pdf(tmp_path / "scanned_empty.pdf", pages=5)

        textbook_id = "tb-empty-mineru-001"
        await storage.create_textbook(
            textbook_id=textbook_id,
            title="Scanned Empty MinerU",
            filepath=str(pdf_path),
        )

        mock_mineru = MagicMock()
        mock_mineru.is_available.return_value = True
        mock_mineru.extract_text_by_pages.return_value = {}  # Empty

        mock_ai = AsyncMock()

        service = TocExtractionService(
            store=storage, filesystem=filesystem,
            ai_provider=mock_ai, mineru_extractor=mock_mineru,
        )
        result = await service.extract_toc(textbook_id)

        # AI should NOT be called (MinerU returned nothing to analyze)
        mock_ai.chat.assert_not_called()

        # Falls back to Full Document
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["title"] == "Full Document"


# ---------------------------------------------------------------------------
# MinerUExtractor page range parameters
# ---------------------------------------------------------------------------


class TestMinerUExtractorPageRange:
    def test_signature_accepts_page_range_params(self):
        """Verify the method signature accepts start_page_id and end_page_id."""
        from app.services.mineru_parser import MinerUExtractor

        extractor = MinerUExtractor()
        # If MinerU is not installed, extractor won't be available
        # but the method should still be callable (returns {})
        result = extractor.extract_text_by_pages(
            b"fake_pdf_bytes",
            output_dir="",
            start_page_id=5,
            end_page_id=10,
        )
        # Without MinerU installed, returns empty dict
        assert result == {}
