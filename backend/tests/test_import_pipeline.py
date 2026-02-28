import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import fitz
import httpx
import pytest

from app.core.config import settings
from app.main import app
from app.routers import textbooks
from app.services.storage import MetadataStore


def create_test_pdf(tmp_path: Path, pages: int = 2) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    doc.save(pdf_path)
    doc.close()
    return pdf_path


async def wait_for_pipeline_status(store: MetadataStore, textbook_id: str, status: str) -> None:
    for _ in range(20):
        textbook = await store.get_textbook(textbook_id)
        if textbook and textbook.get("pipeline_status") == status:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"pipeline_status did not reach {status}")


async def create_course_with_material(store: MetadataStore, tmp_path: Path) -> str:
    course_id = await store.create_course("Import Pipeline Course")
    material_path = tmp_path / "material.txt"
    material_path.write_text("topic one", encoding="utf-8")
    await store.create_university_material(
        course_id=course_id,
        title="Material",
        file_type="txt",
        filepath=str(material_path),
    )
    return course_id


@pytest.mark.asyncio
async def test_import_starts_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path)

    mock_start = AsyncMock(return_value={"pipeline_status": "uploaded"})
    mock_toc = AsyncMock(return_value={"pipeline_status": "toc_extracted", "chapters": []})
    with patch.object(textbooks.PipelineOrchestrator, "start_import", mock_start), patch.object(
        textbooks.PipelineOrchestrator, "run_toc_phase", mock_toc
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["textbook_id"]
        assert data["job_id"]

        await asyncio.sleep(0)
        mock_start.assert_awaited_once()
        mock_toc.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_pauses_after_toc(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path, pages=3)
    toc_entries = [
        {"level": 1, "title": "Intro", "page": 1},
        {"level": 1, "title": "Second", "page": 3},
    ]

    with patch.object(textbooks.PDFParser, "extract_toc", return_value=toc_entries):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

    assert resp.status_code == 200
    textbook_id = resp.json()["textbook_id"]
    store = MetadataStore(db_path=tmp_path / "lazy_learn.db")
    await store.initialize()
    await wait_for_pipeline_status(store, textbook_id, "toc_extracted")

    textbook = await store.get_textbook(textbook_id)
    chapters = await store.list_chapters(textbook_id)
    assert textbook is not None
    assert textbook["pipeline_status"] == "toc_extracted"
    assert len(chapters) == 2


@pytest.mark.asyncio
async def test_import_with_materials_includes_relevance(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path)

    store = MetadataStore(db_path=tmp_path / "lazy_learn.db")
    await store.initialize()
    course_id = await create_course_with_material(store, tmp_path)

    relevance_results = [
        {"chapter_id": "ch1", "relevance_score": 0.9, "matched_topics": ["topic one"]}
    ]
    mock_toc = AsyncMock(
        return_value={
            "pipeline_status": "toc_extracted",
            "chapters": [{"id": "ch1", "title": "Intro", "chapter_number": "1"}],
            "relevance_results": relevance_results,
        }
    )

    with patch.object(textbooks.PipelineOrchestrator, "run_toc_phase", mock_toc):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    data={"course_id": course_id},
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

    assert resp.status_code == 200
    textbook_id = resp.json()["textbook_id"]
    await asyncio.sleep(0)

    job = textbooks._job_status.get(textbook_id, {})
    assert job.get("relevance_results") == relevance_results


@pytest.mark.asyncio
async def test_import_without_materials_skips_relevance(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path)

    store = MetadataStore(db_path=tmp_path / "lazy_learn.db")
    await store.initialize()
    course_id = await store.create_course("Empty Course")

    mock_toc = AsyncMock(
        return_value={
            "pipeline_status": "toc_extracted",
            "chapters": [{"id": "ch1", "title": "Intro", "chapter_number": "1"}],
            "relevance_results": [],
        }
    )

    with patch.object(textbooks.PipelineOrchestrator, "run_toc_phase", mock_toc):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    data={"course_id": course_id},
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

    assert resp.status_code == 200
    textbook_id = resp.json()["textbook_id"]
    await asyncio.sleep(0)

    job = textbooks._job_status.get(textbook_id, {})
    assert job.get("relevance_results", []) == []


@pytest.mark.asyncio
async def test_status_endpoint_returns_pipeline_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path, pages=2)
    toc_entries = [
        {"level": 1, "title": "Intro", "page": 1},
        {"level": 1, "title": "Second", "page": 2},
    ]

    with patch.object(textbooks.PDFParser, "extract_toc", return_value=toc_entries):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

            assert resp.status_code == 200
            textbook_id = resp.json()["textbook_id"]

            store = MetadataStore(db_path=tmp_path / "lazy_learn.db")
            await store.initialize()
            await wait_for_pipeline_status(store, textbook_id, "toc_extracted")

            status = await client.get(f"/api/textbooks/{textbook_id}/status")

    assert status.status_code == 200
    data = status.json()
    assert data["pipeline_status"] == "toc_extracted"
    assert len(data["chapters"]) == 2
    assert data["chapters"][0]["extraction_status"]


@pytest.mark.asyncio
async def test_status_includes_relevance_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    textbooks._job_status.clear()
    pdf_path = create_test_pdf(tmp_path, pages=1)
    toc_entries = [{"level": 1, "title": "Only", "page": 1}]

    with patch.object(textbooks.PDFParser, "extract_toc", return_value=toc_entries):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            with pdf_path.open("rb") as handle:
                resp = await client.post(
                    "/api/textbooks/import",
                    files={"file": ("sample.pdf", handle, "application/pdf")},
                )

            assert resp.status_code == 200
            textbook_id = resp.json()["textbook_id"]

            store = MetadataStore(db_path=tmp_path / "lazy_learn.db")
            await store.initialize()
            await wait_for_pipeline_status(store, textbook_id, "toc_extracted")
            chapters = await store.list_chapters(textbook_id)

            relevance_results = [
                {
                    "chapter_id": chapters[0]["id"],
                    "relevance_score": 0.8,
                    "matched_topics": ["topic one"],
                }
            ]
            textbooks._job_status[textbook_id]["relevance_results"] = relevance_results

            status = await client.get(f"/api/textbooks/{textbook_id}/status")

    assert status.status_code == 200
    data = status.json()
    assert data["relevance_results"] == relevance_results
    assert data["chapters"][0]["relevance_score"] == 0.8
    assert data["chapters"][0]["matched_topics"] == ["topic one"]
