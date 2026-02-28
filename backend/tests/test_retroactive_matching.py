"""Tests for RetroactiveMatcher — verifies matching triggers on material upload."""

from unittest.mock import AsyncMock

from app.models.pipeline_models import RelevanceResult
from app.services.retroactive_matcher import RetroactiveMatcher


def _make_textbook(tb_id: str, pipeline_status: str) -> dict:
    return {"id": tb_id, "title": f"Textbook {tb_id}", "pipeline_status": pipeline_status}


def _make_result(chapter_id: str, score: float) -> RelevanceResult:
    return RelevanceResult(
        chapter_id=chapter_id,
        chapter_title=f"Chapter {chapter_id}",
        relevance_score=score,
        matched_topics=["topic-a"],
        reasoning="test",
    )


COURSE_ID = "course-1"


async def test_new_summary_triggers_matching():
    """Material summarized + textbook with TOC → relevance matching runs."""
    store = AsyncMock()
    store.get_course_textbooks.return_value = [_make_textbook("tb-1", "toc_extracted")]

    matcher = AsyncMock()
    results = [_make_result("ch-1", 0.8)]
    matcher.match_chapters.return_value = results

    retro = RetroactiveMatcher(store, matcher)
    out = await retro.on_material_summarized(COURSE_ID)

    matcher.match_chapters.assert_called_once_with("tb-1", COURSE_ID)
    assert "tb-1" in out
    assert out["tb-1"] == results


async def test_no_textbooks_skips_matching():
    """No textbooks in course → empty dict, matcher never called."""
    store = AsyncMock()
    store.get_course_textbooks.return_value = []

    matcher = AsyncMock()

    retro = RetroactiveMatcher(store, matcher)
    out = await retro.on_material_summarized(COURSE_ID)

    assert out == {}
    matcher.match_chapters.assert_not_called()


async def test_multiple_textbooks_all_matched():
    """Course with 2 qualifying textbooks → both get relevance results."""
    store = AsyncMock()
    store.get_course_textbooks.return_value = [
        _make_textbook("tb-1", "toc_extracted"),
        _make_textbook("tb-2", "partially_extracted"),
    ]

    matcher = AsyncMock()
    matcher.match_chapters.side_effect = [
        [_make_result("ch-1", 0.9)],
        [_make_result("ch-2", 0.5)],
    ]

    retro = RetroactiveMatcher(store, matcher)
    out = await retro.on_material_summarized(COURSE_ID)

    assert len(out) == 2
    assert "tb-1" in out
    assert "tb-2" in out
    assert matcher.match_chapters.call_count == 2


async def test_matching_results_returned():
    """Uploaded and error textbooks are excluded; qualifying ones return results."""
    store = AsyncMock()
    store.get_course_textbooks.return_value = [
        _make_textbook("tb-ok", "fully_extracted"),
        _make_textbook("tb-new", "uploaded"),
        _make_textbook("tb-err", "error"),
    ]

    expected = [_make_result("ch-1", 0.7), _make_result("ch-2", 0.3)]
    matcher = AsyncMock()
    matcher.match_chapters.return_value = expected

    retro = RetroactiveMatcher(store, matcher)
    out = await retro.on_material_summarized(COURSE_ID)

    # Only tb-ok qualifies
    assert list(out.keys()) == ["tb-ok"]
    assert out["tb-ok"] == expected
    matcher.match_chapters.assert_called_once_with("tb-ok", COURSE_ID)
