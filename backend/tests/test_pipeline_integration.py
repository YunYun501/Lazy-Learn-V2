import asyncio
from unittest.mock import AsyncMock, MagicMock, call

from app.models.pipeline_models import ExtractionStatus, PipelineStatus, RelevanceResult
from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.retroactive_matcher import RetroactiveMatcher
from app.services.storage import MetadataStore


def _make_store() -> AsyncMock:
    store = AsyncMock(spec=MetadataStore)
    store.create_textbook = AsyncMock(return_value="tb1")
    store.assign_textbook_to_course = AsyncMock()
    store.update_textbook_pipeline_status = AsyncMock()
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": None})
    store.create_chapter = AsyncMock(return_value="ch1")
    store.create_section = AsyncMock()
    store.list_university_materials = AsyncMock(return_value=[])
    store.list_chapters = AsyncMock(return_value=[])
    store.update_chapter_extraction_status = AsyncMock()
    store.get_chapters_by_extraction_status = AsyncMock(return_value=[])
    store.get_course_textbooks = AsyncMock(return_value=[])
    return store


def _make_toc_service(chapters: list[dict]) -> MagicMock:
    toc_service = MagicMock()
    toc_service.extract_toc = AsyncMock(return_value={"chapters": chapters})
    return toc_service


def _make_relevance_service(results: list[dict]) -> MagicMock:
    relevance_service = MagicMock()
    relevance_service.match_chapters = AsyncMock(return_value=results)
    return relevance_service


def _make_extraction_service() -> MagicMock:
    extraction_service = MagicMock()
    extraction_service.extract = AsyncMock()
    return extraction_service


def _make_orchestrator(
    store: MetadataStore,
    toc,
    relevance,
    extraction,
    description,
) -> PipelineOrchestrator:
    return PipelineOrchestrator(
        store=store,
        toc_service=toc,
        relevance_service=relevance,
        extraction_service=extraction,
        description_service=description,
    )


def _make_toc_chapters(count: int) -> list[dict]:
    chapters: list[dict] = []
    for index in range(1, count + 1):
        chapters.append(
            {
                "chapter_number": str(index),
                "title": f"Chapter {index}",
                "page_start": (index - 1) * 10 + 1,
                "page_end": index * 10,
                "sections": [],
            }
        )
    return chapters


async def test_full_pipeline_textbook_first():
    chapters_payload = _make_toc_chapters(3)
    store = _make_store()
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": None})
    store.create_chapter = AsyncMock(side_effect=["ch1", "ch2", "ch3"])
    store.list_chapters = AsyncMock(
        return_value=[{"id": "ch1"}, {"id": "ch2"}, {"id": "ch3"}]
    )
    store.get_chapters_by_extraction_status = AsyncMock(
        return_value=[{"id": "ch1"}, {"id": "ch2"}]
    )

    toc_service = _make_toc_service(chapters_payload)
    extraction_service = _make_extraction_service()
    orchestrator = _make_orchestrator(
        store, toc_service, None, extraction_service, None
    )

    result = await orchestrator.start_import("tb1", None, "/tmp/book.pdf")
    assert result["pipeline_status"] == PipelineStatus.uploaded.value

    toc_result = await orchestrator.run_toc_phase("tb1")
    assert toc_result["pipeline_status"] == PipelineStatus.toc_extracted.value
    assert len(toc_result["chapters"]) == 3

    verification = await orchestrator.submit_verification("tb1", ["ch1", "ch2"])
    assert verification["pipeline_status"] == PipelineStatus.extracting.value

    extraction = await orchestrator.run_extraction_phase("tb1", ["ch1", "ch2"])
    assert extraction["pipeline_status"] == PipelineStatus.partially_extracted.value

    extraction_service.extract.assert_awaited_once_with("tb1", ["ch1", "ch2"])
    store.update_chapter_extraction_status.assert_has_awaits(
        [
            call("ch1", ExtractionStatus.extracting.value),
            call("ch2", ExtractionStatus.extracting.value),
            call("ch3", ExtractionStatus.deferred.value),
            call("ch1", ExtractionStatus.extracted.value),
            call("ch2", ExtractionStatus.extracted.value),
        ],
        any_order=True,
    )


async def test_full_pipeline_with_materials():
    chapters_payload = _make_toc_chapters(2)
    store = _make_store()
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": "course1"})
    store.list_university_materials = AsyncMock(return_value=[{"id": "m1"}])
    store.create_chapter = AsyncMock(side_effect=["ch1", "ch2"])
    store.list_chapters = AsyncMock(return_value=[{"id": "ch1"}, {"id": "ch2"}])
    store.get_chapters_by_extraction_status = AsyncMock(
        return_value=[{"id": "ch1"}, {"id": "ch2"}]
    )

    toc_service = _make_toc_service(chapters_payload)
    relevance_results = [
        {"chapter_id": "ch1", "score": 0.9},
        {"chapter_id": "ch2", "score": 0.4},
    ]
    relevance_service = _make_relevance_service(relevance_results)
    extraction_service = _make_extraction_service()
    orchestrator = _make_orchestrator(
        store, toc_service, relevance_service, extraction_service, None
    )

    result = await orchestrator.start_import("tb1", "course1", "/tmp/book.pdf")
    assert result["pipeline_status"] == PipelineStatus.uploaded.value

    toc_result = await orchestrator.run_toc_phase("tb1")
    assert toc_result["relevance_results"] == relevance_results
    relevance_service.match_chapters.assert_awaited_once_with(
        "tb1",
        "course1",
    )

    verification = await orchestrator.submit_verification("tb1", ["ch1", "ch2"])
    assert verification["pipeline_status"] == PipelineStatus.extracting.value

    extraction = await orchestrator.run_extraction_phase("tb1", ["ch1", "ch2"])
    assert extraction["pipeline_status"] == PipelineStatus.fully_extracted.value


async def test_retroactive_matching_flow():
    store = _make_store()
    store.get_course_textbooks = AsyncMock(
        return_value=[{"id": "tb1", "pipeline_status": PipelineStatus.toc_extracted.value}]
    )
    relevance_matcher = AsyncMock()
    relevance_matcher.match_chapters = AsyncMock(
        return_value=[
            RelevanceResult(
                chapter_id="ch1",
                chapter_title="Chapter 1",
                relevance_score=0.6,
                matched_topics=["topic"],
                reasoning="match",
            )
        ]
    )

    retro = RetroactiveMatcher(store, relevance_matcher)
    results = await retro.on_material_summarized("course1")

    relevance_matcher.match_chapters.assert_awaited_once_with("tb1", "course1")
    assert "tb1" in results


async def test_deferred_extraction_flow():
    chapters_payload = _make_toc_chapters(5)
    store = _make_store()
    store.get_textbook = AsyncMock(return_value={"id": "tb1", "course_id": None})
    store.create_chapter = AsyncMock(
        side_effect=["ch1", "ch2", "ch3", "ch4", "ch5"]
    )
    store.list_chapters = AsyncMock(
        return_value=[
            {"id": "ch1"},
            {"id": "ch2"},
            {"id": "ch3"},
            {"id": "ch4"},
            {"id": "ch5"},
        ]
    )
    store.get_chapters_by_extraction_status = AsyncMock(
        side_effect=[
            [{"id": "ch1"}, {"id": "ch2"}],
            [
                {"id": "ch1"},
                {"id": "ch2"},
                {"id": "ch3"},
                {"id": "ch4"},
                {"id": "ch5"},
            ],
        ]
    )

    toc_service = _make_toc_service(chapters_payload)
    extraction_service = _make_extraction_service()
    orchestrator = _make_orchestrator(
        store, toc_service, None, extraction_service, None
    )

    await orchestrator.start_import("tb1", None, "/tmp/book.pdf")
    await orchestrator.run_toc_phase("tb1")
    await orchestrator.submit_verification("tb1", ["ch1", "ch2"])

    extraction = await orchestrator.run_extraction_phase("tb1", ["ch1", "ch2"])
    assert extraction["pipeline_status"] == PipelineStatus.partially_extracted.value

    deferred = await orchestrator.run_deferred_extraction(
        "tb1", ["ch3", "ch4", "ch5"]
    )
    assert deferred["pipeline_status"] == PipelineStatus.extracting.value

    final = await orchestrator.run_extraction_phase("tb1", ["ch3", "ch4", "ch5"])
    assert final["pipeline_status"] == PipelineStatus.fully_extracted.value

    extraction_service.extract.assert_has_awaits(
        [call("tb1", ["ch1", "ch2"]), call("tb1", ["ch3", "ch4", "ch5"])],
        any_order=False,
    )
    store.update_chapter_extraction_status.assert_has_awaits(
        [
            call("ch1", ExtractionStatus.extracting.value),
            call("ch2", ExtractionStatus.extracting.value),
            call("ch3", ExtractionStatus.deferred.value),
            call("ch4", ExtractionStatus.deferred.value),
            call("ch5", ExtractionStatus.deferred.value),
            call("ch3", ExtractionStatus.extracting.value),
            call("ch4", ExtractionStatus.extracting.value),
            call("ch5", ExtractionStatus.extracting.value),
            call("ch1", ExtractionStatus.extracted.value),
            call("ch2", ExtractionStatus.extracted.value),
            call("ch3", ExtractionStatus.extracted.value),
            call("ch4", ExtractionStatus.extracted.value),
            call("ch5", ExtractionStatus.extracted.value),
        ],
        any_order=True,
    )


async def test_single_chapter_book_flow():
    chapters_payload = _make_toc_chapters(1)
    store = _make_store()
    store.create_chapter = AsyncMock(side_effect=["ch1"])
    store.list_chapters = AsyncMock(return_value=[{"id": "ch1"}])
    store.get_chapters_by_extraction_status = AsyncMock(return_value=[{"id": "ch1"}])

    toc_service = _make_toc_service(chapters_payload)
    extraction_service = _make_extraction_service()
    orchestrator = _make_orchestrator(
        store, toc_service, None, extraction_service, None
    )

    await orchestrator.start_import("tb1", None, "/tmp/book.pdf")
    await orchestrator.run_toc_phase("tb1")
    await orchestrator.submit_verification("tb1", ["ch1"])
    extraction = await orchestrator.run_extraction_phase("tb1", ["ch1"])
    assert extraction["pipeline_status"] == PipelineStatus.fully_extracted.value


async def test_concurrent_imports():
    chapters_payload_1 = _make_toc_chapters(2)
    chapters_payload_2 = _make_toc_chapters(2)

    store_1 = _make_store()
    store_1.create_chapter = AsyncMock(side_effect=["tb1-ch1", "tb1-ch2"])
    store_1.list_chapters = AsyncMock(
        return_value=[{"id": "tb1-ch1"}, {"id": "tb1-ch2"}]
    )
    store_1.get_chapters_by_extraction_status = AsyncMock(
        return_value=[{"id": "tb1-ch1"}, {"id": "tb1-ch2"}]
    )

    store_2 = _make_store()
    store_2.create_chapter = AsyncMock(side_effect=["tb2-ch1", "tb2-ch2"])
    store_2.list_chapters = AsyncMock(
        return_value=[{"id": "tb2-ch1"}, {"id": "tb2-ch2"}]
    )
    store_2.get_chapters_by_extraction_status = AsyncMock(
        return_value=[{"id": "tb2-ch1"}, {"id": "tb2-ch2"}]
    )

    orchestrator_1 = _make_orchestrator(
        store_1,
        _make_toc_service(chapters_payload_1),
        None,
        _make_extraction_service(),
        None,
    )
    orchestrator_2 = _make_orchestrator(
        store_2,
        _make_toc_service(chapters_payload_2),
        None,
        _make_extraction_service(),
        None,
    )

    async def _run_pipeline(orchestrator: PipelineOrchestrator, textbook_id: str) -> str:
        await orchestrator.start_import(textbook_id, None, f"/tmp/{textbook_id}.pdf")
        await orchestrator.run_toc_phase(textbook_id)
        await orchestrator.submit_verification(
            textbook_id, [f"{textbook_id}-ch1", f"{textbook_id}-ch2"]
        )
        final = await orchestrator.run_extraction_phase(
            textbook_id, [f"{textbook_id}-ch1", f"{textbook_id}-ch2"]
        )
        return final["pipeline_status"]

    results = await asyncio.gather(
        _run_pipeline(orchestrator_1, "tb1"),
        _run_pipeline(orchestrator_2, "tb2"),
    )
    assert results == [PipelineStatus.fully_extracted.value] * 2

    assert all(
        call_args.args[0] == "tb1"
        for call_args in store_1.update_textbook_pipeline_status.await_args_list
    )
    assert all(
        call_args.args[0] == "tb2"
        for call_args in store_2.update_textbook_pipeline_status.await_args_list
    )


async def test_error_recovery():
    store = _make_store()
    store.update_textbook_pipeline_status = AsyncMock()
    extraction_service = _make_extraction_service()
    extraction_service.extract = AsyncMock(side_effect=RuntimeError("boom"))
    description_service = MagicMock()
    description_service.generate = AsyncMock()

    orchestrator = _make_orchestrator(
        store, None, None, extraction_service, description_service
    )
    result = await orchestrator.run_extraction_phase("tb1", ["ch1"])

    assert result["pipeline_status"] == PipelineStatus.error.value
    store.update_textbook_pipeline_status.assert_awaited_with(
        "tb1", PipelineStatus.error.value
    )

    await orchestrator.run_description_phase("tb1", ["ch1"])
    description_service.generate.assert_awaited_once_with("tb1", ["ch1"])
