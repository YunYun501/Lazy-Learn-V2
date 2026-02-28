import pytest
from unittest.mock import AsyncMock, MagicMock, call

from app.models.pipeline_models import PipelineStatus, ExtractionStatus
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.storage import MetadataStore


class FakeTocService:
    async def extract_toc(self, textbook_id: str) -> dict:
        return {
            "chapters": [
                {
                    "chapter_number": "1",
                    "title": "Intro",
                    "page_start": 1,
                    "page_end": 5,
                    "sections": [
                        {
                            "section_number": 1,
                            "title": "Basics",
                            "page_start": 1,
                            "page_end": 2,
                        }
                    ],
                }
            ]
        }


@pytest.mark.asyncio
async def test_start_pipeline_sets_uploaded():
    store = AsyncMock(spec=MetadataStore)
    store.create_textbook = AsyncMock(return_value="tb1")
    store.update_textbook_pipeline_status = AsyncMock()

    orchestrator = PipelineOrchestrator(store=store)
    result = await orchestrator.start_import(
        textbook_id="tb1",
        course_id=None,
        file_path="/tmp/book.pdf",
    )

    assert result["pipeline_status"] == PipelineStatus.uploaded.value
    store.update_textbook_pipeline_status.assert_awaited_once_with(
        "tb1",
        PipelineStatus.uploaded.value,
    )


@pytest.mark.asyncio
async def test_toc_phase_transitions_to_toc_extracted():
    store = AsyncMock(spec=MetadataStore)
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": None})
    store.create_chapter = AsyncMock(return_value="ch1")
    store.create_section = AsyncMock()
    store.update_textbook_pipeline_status = AsyncMock()

    toc_service = MagicMock()
    toc_service.extract_toc = AsyncMock(
        return_value={
            "chapters": [
                {
                    "chapter_number": "1",
                    "title": "Intro",
                    "page_start": 1,
                    "page_end": 10,
                    "sections": [],
                }
            ]
        }
    )

    orchestrator = PipelineOrchestrator(store=store, toc_service=toc_service)
    result = await orchestrator.run_toc_phase("tb1")

    assert len(result["chapters"]) == 1
    store.update_textbook_pipeline_status.assert_awaited_once_with(
        "tb1",
        PipelineStatus.toc_extracted.value,
    )


@pytest.mark.asyncio
async def test_toc_phase_without_materials_skips_relevance():
    store = AsyncMock(spec=MetadataStore)
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": "c1"})
    store.list_university_materials = AsyncMock(return_value=[])
    store.create_chapter = AsyncMock(return_value="ch1")
    store.create_section = AsyncMock()
    store.update_textbook_pipeline_status = AsyncMock()

    toc_service = MagicMock()
    toc_service.extract_toc = AsyncMock(
        return_value={
            "chapters": [
                {
                    "chapter_number": "1",
                    "title": "Intro",
                    "page_start": 1,
                    "page_end": 10,
                    "sections": [],
                }
            ]
        }
    )
    relevance_service = MagicMock()
    relevance_service.match = AsyncMock(return_value=[{"chapter_id": "ch1"}])

    orchestrator = PipelineOrchestrator(
        store=store,
        toc_service=toc_service,
        relevance_service=relevance_service,
    )
    result = await orchestrator.run_toc_phase("tb1")

    assert result["relevance_results"] == []
    relevance_service.match.assert_not_awaited()


@pytest.mark.asyncio
async def test_toc_phase_with_materials_includes_relevance():
    store = AsyncMock(spec=MetadataStore)
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": "c1"})
    store.list_university_materials = AsyncMock(return_value=[{"id": "m1"}])
    store.create_chapter = AsyncMock(return_value="ch1")
    store.create_section = AsyncMock()
    store.update_textbook_pipeline_status = AsyncMock()

    toc_service = MagicMock()
    toc_service.extract_toc = AsyncMock(
        return_value={
            "chapters": [
                {
                    "chapter_number": "1",
                    "title": "Intro",
                    "page_start": 1,
                    "page_end": 10,
                    "sections": [],
                }
            ]
        }
    )
    relevance_service = MagicMock()
    relevance_service.match = AsyncMock(return_value=[{"chapter_id": "ch1", "score": 0.5}])

    orchestrator = PipelineOrchestrator(
        store=store,
        toc_service=toc_service,
        relevance_service=relevance_service,
    )
    result = await orchestrator.run_toc_phase("tb1")

    assert result["relevance_results"] == [{"chapter_id": "ch1", "score": 0.5}]
    relevance_service.match.assert_awaited_once()


@pytest.mark.asyncio
async def test_verification_transitions_to_awaiting():
    store = AsyncMock(spec=MetadataStore)
    store.list_chapters = AsyncMock(return_value=[{"id": "c1"}])
    store.update_textbook_pipeline_status = AsyncMock()
    store.update_chapter_extraction_status = AsyncMock()

    orchestrator = PipelineOrchestrator(store=store)
    await orchestrator.submit_verification("tb1", ["c1"])

    assert call("tb1", PipelineStatus.awaiting_verification.value) in (
        store.update_textbook_pipeline_status.await_args_list
    )


@pytest.mark.asyncio
async def test_extraction_phase_starts_for_selected():
    store = AsyncMock(spec=MetadataStore)
    store.list_chapters = AsyncMock(return_value=[{"id": "c1"}, {"id": "c2"}])
    store.update_textbook_pipeline_status = AsyncMock()
    store.update_chapter_extraction_status = AsyncMock()

    orchestrator = PipelineOrchestrator(store=store)
    await orchestrator.submit_verification("tb1", ["c1"])

    store.update_chapter_extraction_status.assert_has_awaits(
        [
            call("c1", ExtractionStatus.extracting.value),
            call("c2", ExtractionStatus.deferred.value),
        ],
        any_order=True,
    )


@pytest.mark.asyncio
async def test_extraction_complete_transitions():
    store = AsyncMock(spec=MetadataStore)
    store.list_chapters = AsyncMock(
        return_value=[{"id": "c1"}, {"id": "c2"}, {"id": "c3"}]
    )
    store.get_chapters_by_extraction_status = AsyncMock(
        return_value=[{"id": "c1"}, {"id": "c2"}]
    )
    store.update_chapter_extraction_status = AsyncMock()
    store.update_textbook_pipeline_status = AsyncMock()

    orchestrator = PipelineOrchestrator(store=store)
    result = await orchestrator.run_extraction_phase("tb1", ["c1", "c2"])

    assert result["pipeline_status"] == PipelineStatus.partially_extracted.value
    store.update_textbook_pipeline_status.assert_awaited_once_with(
        "tb1",
        PipelineStatus.partially_extracted.value,
    )


@pytest.mark.asyncio
async def test_deferred_extraction_works():
    store = AsyncMock(spec=MetadataStore)
    store.update_chapter_extraction_status = AsyncMock()

    orchestrator = PipelineOrchestrator(store=store)
    await orchestrator.run_deferred_extraction("tb1", ["c2", "c3"])

    store.update_chapter_extraction_status.assert_has_awaits(
        [
            call("c2", ExtractionStatus.extracting.value),
            call("c3", ExtractionStatus.extracting.value),
        ],
        any_order=True,
    )


@pytest.mark.asyncio
async def test_error_handling_sets_error_status():
    store = AsyncMock(spec=MetadataStore)
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": None})
    store.update_textbook_pipeline_status = AsyncMock()

    toc_service = MagicMock()
    toc_service.extract_toc = AsyncMock(side_effect=RuntimeError("boom"))

    orchestrator = PipelineOrchestrator(store=store, toc_service=toc_service)
    result = await orchestrator.run_toc_phase("tb1")

    assert result["pipeline_status"] == PipelineStatus.error.value
    assert "boom" in result["error"]
    store.update_textbook_pipeline_status.assert_awaited_once_with(
        "tb1",
        PipelineStatus.error.value,
    )


@pytest.mark.asyncio
async def test_pipeline_state_persists_across_restart(tmp_path):
    db_path = tmp_path / "test.db"
    store_1 = MetadataStore(db_path=db_path)
    await store_1.initialize()
    textbook_id = await store_1.create_textbook(
        title="Test Book",
        filepath="/tmp/book.pdf",
    )

    orchestrator = PipelineOrchestrator(store=store_1, toc_service=FakeTocService())
    await orchestrator.run_toc_phase(textbook_id)

    store_2 = MetadataStore(db_path=db_path)
    await store_2.initialize()
    textbook = await store_2.get_textbook(textbook_id)

    assert textbook["pipeline_status"] == PipelineStatus.toc_extracted.value
