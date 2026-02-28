"""Tests for the RelevanceMatcher service (TDD — tests written first)."""
import json
from unittest.mock import AsyncMock, MagicMock


from app.services.relevance_matcher import RelevanceMatcher
from app.models.pipeline_models import RelevanceResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_MATERIALS = [
    {"id": "mat_1", "course_id": "course_1", "title": "Lecture Notes"},
]

SAMPLE_SUMMARY = {
    "id": "sum_1",
    "material_id": "mat_1",
    "course_id": "course_1",
    "summary_json": json.dumps(
        {
            "topics": [
                {"title": "Integration", "description": "Definite and indefinite integrals"},
                {"title": "Derivatives", "description": "Chain rule and product rule"},
            ]
        }
    ),
}

SAMPLE_CHAPTERS = [
    {
        "id": "ch_1",
        "textbook_id": "tb_1",
        "chapter_number": "1",
        "title": "Calculus Basics",
        "page_start": 1,
        "page_end": 20,
    },
    {
        "id": "ch_2",
        "textbook_id": "tb_1",
        "chapter_number": "2",
        "title": "Advanced Integration",
        "page_start": 21,
        "page_end": 40,
    },
    {
        "id": "ch_3",
        "textbook_id": "tb_1",
        "chapter_number": "3",
        "title": "Linear Algebra Intro",
        "page_start": 41,
        "page_end": 60,
    },
]

# AI returns chapters in non-sorted order (ch_1 then ch_2 then ch_3)
SAMPLE_AI_RESPONSE = {
    "results": [
        {
            "chapter_id": "ch_1",
            "chapter_title": "Calculus Basics",
            "relevance_score": 0.6,
            "matched_topics": ["Derivatives"],
            "reasoning": "Covers derivative basics",
        },
        {
            "chapter_id": "ch_2",
            "chapter_title": "Advanced Integration",
            "relevance_score": 0.9,
            "matched_topics": ["Integration", "Derivatives"],
            "reasoning": "Covers integration and related derivative techniques",
        },
        {
            "chapter_id": "ch_3",
            "chapter_title": "Linear Algebra Intro",
            "relevance_score": 0.1,
            "matched_topics": [],
            "reasoning": "Not directly related to calculus topics",
        },
    ]
}


def _make_store(materials=None, summary=None, chapters=None):
    """Return a fully-mocked MetadataStore."""
    store = MagicMock()
    store.list_university_materials = AsyncMock(
        return_value=materials if materials is not None else []
    )
    store.get_material_summary = AsyncMock(return_value=summary)
    store.list_chapters = AsyncMock(
        return_value=chapters if chapters is not None else []
    )
    return store


def _make_router(response=None):
    """Return a mocked AIRouter with a get_json_response async stub."""
    router = MagicMock()
    router.get_json_response = AsyncMock(return_value=response or {})
    return router


# ---------------------------------------------------------------------------
# Test 1 — match_chapters returns a RelevanceResult per chapter
# ---------------------------------------------------------------------------


async def test_match_chapters_to_summaries():
    """Mock DeepSeek → returns relevance scores for each chapter."""
    store = _make_store(
        materials=SAMPLE_MATERIALS,
        summary=SAMPLE_SUMMARY,
        chapters=SAMPLE_CHAPTERS,
    )
    router = _make_router(response=SAMPLE_AI_RESPONSE)

    matcher = RelevanceMatcher(store=store, ai_router=router)
    results = await matcher.match_chapters("tb_1", "course_1")

    assert len(results) == 3
    assert all(isinstance(r, RelevanceResult) for r in results)
    router.get_json_response.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2 — empty material summaries → empty list, no DeepSeek call
# ---------------------------------------------------------------------------


async def test_no_materials_returns_empty():
    """No material summaries → returns empty list, DeepSeek NOT called."""
    store = _make_store(materials=[])
    router = _make_router()

    matcher = RelevanceMatcher(store=store, ai_router=router)
    results = await matcher.match_chapters("tb_1", "course_1")

    assert results == []
    router.get_json_response.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3 — all scores clamped to [0.0, 1.0]
# ---------------------------------------------------------------------------


async def test_relevance_scores_between_0_and_1():
    """Scores outside 0.0-1.0 are clamped before returning."""
    store = _make_store(
        materials=SAMPLE_MATERIALS,
        summary=SAMPLE_SUMMARY,
        chapters=SAMPLE_CHAPTERS,
    )
    # AI returns one score above 1 and one below 0 to test clamping
    out_of_range_response = {
        "results": [
            {
                "chapter_id": "ch_1",
                "chapter_title": "Calculus Basics",
                "relevance_score": 1.5,   # should be clamped to 1.0
                "matched_topics": [],
                "reasoning": "",
            },
            {
                "chapter_id": "ch_2",
                "chapter_title": "Advanced Integration",
                "relevance_score": -0.3,  # should be clamped to 0.0
                "matched_topics": [],
                "reasoning": "",
            },
            {
                "chapter_id": "ch_3",
                "chapter_title": "Linear Algebra Intro",
                "relevance_score": 0.7,   # already in range
                "matched_topics": [],
                "reasoning": "",
            },
        ]
    }
    router = _make_router(response=out_of_range_response)

    matcher = RelevanceMatcher(store=store, ai_router=router)
    results = await matcher.match_chapters("tb_1", "course_1")

    for r in results:
        assert 0.0 <= r.relevance_score <= 1.0, (
            f"Score {r.relevance_score} for '{r.chapter_title}' is out of range"
        )


# ---------------------------------------------------------------------------
# Test 4 — results are sorted by relevance_score descending
# ---------------------------------------------------------------------------


async def test_chapters_ranked_by_relevance():
    """Results are sorted highest → lowest relevance_score."""
    store = _make_store(
        materials=SAMPLE_MATERIALS,
        summary=SAMPLE_SUMMARY,
        chapters=SAMPLE_CHAPTERS,
    )
    # AI returns chapters in ch_1 (0.6), ch_2 (0.9), ch_3 (0.1) order
    router = _make_router(response=SAMPLE_AI_RESPONSE)

    matcher = RelevanceMatcher(store=store, ai_router=router)
    results = await matcher.match_chapters("tb_1", "course_1")

    scores = [r.relevance_score for r in results]
    assert scores == sorted(scores, reverse=True), (
        f"Expected descending order, got {scores}"
    )
    # ch_2 (0.9) should be first
    assert results[0].chapter_id == "ch_2"


# ---------------------------------------------------------------------------
# Test 5 — each result includes which material topics matched
# ---------------------------------------------------------------------------


async def test_matched_topics_populated():
    """Each RelevanceResult includes a populated matched_topics list."""
    store = _make_store(
        materials=SAMPLE_MATERIALS,
        summary=SAMPLE_SUMMARY,
        chapters=SAMPLE_CHAPTERS,
    )
    router = _make_router(response=SAMPLE_AI_RESPONSE)

    matcher = RelevanceMatcher(store=store, ai_router=router)
    results = await matcher.match_chapters("tb_1", "course_1")

    for r in results:
        assert isinstance(r.matched_topics, list)

    # The highest-scored chapter (ch_2) should list both matched topics
    best = results[0]  # sorted descending → ch_2
    assert "Integration" in best.matched_topics
    assert "Derivatives" in best.matched_topics
