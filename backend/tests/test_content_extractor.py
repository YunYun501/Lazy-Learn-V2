import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.pipeline_models import ContentType
from app.services.content_extractor import ContentExtractor


def _write_content_list(output_dir: str, entries: list[dict]) -> None:
    content_dir = Path(output_dir) / "document" / "auto"
    content_dir.mkdir(parents=True, exist_ok=True)
    content_path = content_dir / "document_content_list.json"
    content_path.write_text(json.dumps(entries), encoding="utf-8")


def _make_store(chapters: list[dict]) -> MagicMock:
    store = MagicMock()
    store.list_chapters = AsyncMock(return_value=chapters)
    store.create_extracted_content = AsyncMock(return_value="content-id")
    store.update_chapter_extraction_status = AsyncMock()
    store.create_section = AsyncMock(return_value="section-id")
    return store


def _make_entries() -> list[dict]:
    return [
        {"type": "text", "text": "Intro", "page_idx": 0},
        {"type": "equation", "text": "E=mc^2", "text_format": "latex", "page_idx": 0},
        {"type": "image", "img_path": "images/fig1.png", "image_caption": ["Figure 1"], "image_footnote": [], "page_idx": 0},
        {"type": "table", "text": "A|B", "img_path": "images/table1.png", "page_idx": 1},
        {"type": "discarded", "text": "Header", "page_idx": 1},
    ]


async def test_extract_single_chapter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 5,
            "page_end": 6,
        }
    ]
    store = _make_store(chapters)
    extractor = ContentExtractor(store)
    entries = _make_entries()

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse) as mocked:
        results = await extractor.extract_chapters("tb-1", ["chapter-1"], "dummy.pdf")

    assert mocked.call_count == 1
    _, kwargs = mocked.call_args
    assert kwargs["start_page_id"] == 4
    assert kwargs["end_page_id"] == 5
    assert results
    assert {item.page_number for item in results} == {5, 6}


async def test_content_types_separated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 1,
            "page_end": 2,
        }
    ]
    store = _make_store(chapters)
    extractor = ContentExtractor(store)
    entries = _make_entries()

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse):
        await extractor.extract_chapters("tb-1", ["chapter-1"], "dummy.pdf")

    stored_types = [call.args[0]["content_type"] for call in store.create_extracted_content.call_args_list]
    assert ContentType.text.value in stored_types
    assert ContentType.table.value in stored_types
    assert ContentType.equation.value in stored_types
    assert ContentType.figure.value in stored_types


async def test_content_stored_in_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 1,
            "page_end": 1,
        }
    ]
    store = _make_store(chapters)
    extractor = ContentExtractor(store)
    entries = [{"type": "text", "text": "Hello", "page_idx": 0}]

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse):
        await extractor.extract_chapters("tb-1", ["chapter-1"], "dummy.pdf")

    assert store.create_extracted_content.await_count == 1
    stored = store.create_extracted_content.call_args.args[0]
    assert stored["chapter_id"] == "chapter-1"


async def test_content_files_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 1,
            "page_end": 1,
        }
    ]
    store = _make_store(chapters)
    extractor = ContentExtractor(store)
    entries = [{"type": "text", "text": "Hello", "page_idx": 0}]

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse):
        await extractor.extract_chapters("tb-1", ["chapter-1"], "dummy.pdf")

    content_dir = tmp_path / "data" / "textbooks" / "tb-1" / "chapters" / "1" / "content"
    files = list(content_dir.glob("*.md"))
    assert len(files) == 1


async def test_batch_contiguous_chapters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 1,
            "page_end": 2,
        },
        {
            "id": "chapter-2",
            "chapter_number": "2",
            "page_start": 3,
            "page_end": 4,
        },
    ]
    store = _make_store(chapters)
    extractor = ContentExtractor(store)
    entries = [
        {"type": "text", "text": "Ch1", "page_idx": 0},
        {"type": "text", "text": "Ch2", "page_idx": 2},
    ]

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse) as mocked:
        await extractor.extract_chapters("tb-1", ["chapter-1", "chapter-2"], "dummy.pdf")

    assert mocked.call_count == 1
    _, kwargs = mocked.call_args
    assert kwargs["start_page_id"] == 0
    assert kwargs["end_page_id"] == 3


async def test_partial_failure_marks_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapters = [
        {
            "id": "chapter-1",
            "chapter_number": "1",
            "page_start": 1,
            "page_end": 1,
        },
        {
            "id": "chapter-2",
            "chapter_number": "2",
            "page_start": 2,
            "page_end": 2,
        },
    ]
    store = _make_store(chapters)

    def _create_content(content_data: dict):
        if content_data["chapter_id"] == "chapter-1":
            raise RuntimeError("DB error")
        return "content-id"

    store.create_extracted_content = AsyncMock(side_effect=_create_content)
    extractor = ContentExtractor(store)
    entries = [
        {"type": "text", "text": "Ch1", "page_idx": 0},
        {"type": "text", "text": "Ch2", "page_idx": 1},
    ]

    def _do_parse(**kwargs):
        _write_content_list(kwargs["output_dir"], entries)
        return kwargs["output_dir"]

    with patch("app.services.content_extractor.do_parse", side_effect=_do_parse):
        await extractor.extract_chapters("tb-1", ["chapter-1", "chapter-2"], "dummy.pdf")

    status_calls = [call.args for call in store.update_chapter_extraction_status.call_args_list]
    assert ("chapter-1", "error") in status_calls
    assert ("chapter-2", "extracted") in status_calls


async def test_sections_created_from_toc():
    store = _make_store([])
    extractor = ContentExtractor(store)
    toc_entries = [
        {"level": 1, "title": "Chapter 1", "page": 1},
        {"level": 2, "title": "Section 1.1", "page": 2},
        {"level": 2, "title": "Section 1.2", "page": 5},
        {"level": 1, "title": "Chapter 2", "page": 9},
    ]

    sections = await extractor.extract_sections("tb-1", "chapter-1", toc_entries)

    assert len(sections) == 2
    store.create_section.assert_awaited()
    stored = store.create_section.call_args_list[0].args[0]
    assert stored["chapter_id"] == "chapter-1"
    assert stored["page_start"] == 2
    assert stored["page_end"] == 4
