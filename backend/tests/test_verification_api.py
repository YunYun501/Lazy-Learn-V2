"""Tests for chapter verification and deferred extraction API endpoints."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TEXTBOOK_ID = "test-textbook-abc123"


def make_textbook(pipeline_status: str) -> dict:
    return {
        "id": TEXTBOOK_ID,
        "title": "Test Textbook",
        "pipeline_status": pipeline_status,
        "filepath": "/test/path.pdf",
        "course": None,
        "library_type": "course",
        "created_at": "2024-01-01T00:00:00",
        "course_id": None,
    }


CHAPTERS = [
    {
        "id": "ch-1",
        "textbook_id": TEXTBOOK_ID,
        "title": "Introduction",
        "chapter_number": "1",
        "page_start": 1,
        "page_end": 20,
        "extraction_status": "pending",
    },
    {
        "id": "ch-2",
        "textbook_id": TEXTBOOK_ID,
        "title": "Chapter 2",
        "chapter_number": "2",
        "page_start": 21,
        "page_end": 40,
        "extraction_status": "pending",
    },
    {
        "id": "ch-3",
        "textbook_id": TEXTBOOK_ID,
        "title": "Chapter 3",
        "chapter_number": "3",
        "page_start": 41,
        "page_end": 60,
        "extraction_status": "deferred",
    },
]


# ---------------------------------------------------------------------------
# Test 1 — verify-chapters returns 200 and starts extraction
# ---------------------------------------------------------------------------


def test_verify_chapters_starts_extraction():
    """POST /textbooks/{id}/verify-chapters with selected IDs → 200, extraction starts."""
    with (
        patch("app.routers.textbooks.get_storage") as mock_get_storage,
        patch("app.routers.textbooks.PipelineOrchestrator") as MockOrch,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("toc_extracted")

        mock_orch = AsyncMock()
        MockOrch.return_value = mock_orch
        mock_orch.submit_verification.return_value = {
            "textbook_id": TEXTBOOK_ID,
            "pipeline_status": "extracting",
        }
        mock_orch.run_extraction_phase.return_value = {
            "textbook_id": TEXTBOOK_ID,
            "pipeline_status": "fully_extracted",
        }

        resp = client.post(
            f"/api/textbooks/{TEXTBOOK_ID}/verify-chapters",
            json={"selected_chapter_ids": ["ch-1", "ch-2"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "extracting"
    assert data["selected_count"] == 2


# ---------------------------------------------------------------------------
# Test 2 — submit_verification called with correct IDs → unselected get deferred
# ---------------------------------------------------------------------------


def test_verify_sets_deferred():
    """Unselected chapters get extraction_status = 'deferred' via submit_verification."""
    with (
        patch("app.routers.textbooks.get_storage") as mock_get_storage,
        patch("app.routers.textbooks.PipelineOrchestrator") as MockOrch,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("toc_extracted")

        mock_orch = AsyncMock()
        MockOrch.return_value = mock_orch
        mock_orch.submit_verification.return_value = {
            "textbook_id": TEXTBOOK_ID,
            "pipeline_status": "extracting",
        }
        mock_orch.run_extraction_phase.return_value = None

        resp = client.post(
            f"/api/textbooks/{TEXTBOOK_ID}/verify-chapters",
            json={"selected_chapter_ids": ["ch-1"]},  # ch-2 and ch-3 unselected → deferred
        )

    assert resp.status_code == 200
    # The orchestrator's submit_verification is what sets unselected chapters to deferred;
    # verify it was called with exactly the selected IDs provided.
    mock_orch.submit_verification.assert_called_once_with(TEXTBOOK_ID, ["ch-1"])


# ---------------------------------------------------------------------------
# Test 3 — verify-chapters requires toc_extracted state
# ---------------------------------------------------------------------------


def test_verify_requires_toc_extracted_state():
    """POST verify-chapters on a textbook in 'uploaded' state → 409 Conflict."""
    with patch("app.routers.textbooks.get_storage") as mock_get_storage:
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("uploaded")

        resp = client.post(
            f"/api/textbooks/{TEXTBOOK_ID}/verify-chapters",
            json={"selected_chapter_ids": ["ch-1"]},
        )

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Test 4 — extract-deferred returns 200 and starts extraction
# ---------------------------------------------------------------------------


def test_deferred_extraction_endpoint():
    """POST /textbooks/{id}/extract-deferred with chapter IDs → 200, extraction starts."""
    with (
        patch("app.routers.textbooks.get_storage") as mock_get_storage,
        patch("app.routers.textbooks.PipelineOrchestrator") as MockOrch,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("partially_extracted")

        mock_orch = AsyncMock()
        MockOrch.return_value = mock_orch
        mock_orch.run_deferred_extraction.return_value = {
            "textbook_id": TEXTBOOK_ID,
            "pipeline_status": "extracting",
        }
        mock_orch.run_extraction_phase.return_value = {
            "textbook_id": TEXTBOOK_ID,
            "pipeline_status": "fully_extracted",
        }

        resp = client.post(
            f"/api/textbooks/{TEXTBOOK_ID}/extract-deferred",
            json={"chapter_ids": ["ch-3"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "extracting"


# ---------------------------------------------------------------------------
# Test 5 — extract-deferred requires partially_extracted or fully_extracted state
# ---------------------------------------------------------------------------


def test_deferred_requires_partially_extracted():
    """POST extract-deferred on a textbook in wrong state → 409 Conflict."""
    with patch("app.routers.textbooks.get_storage") as mock_get_storage:
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("toc_extracted")

        resp = client.post(
            f"/api/textbooks/{TEXTBOOK_ID}/extract-deferred",
            json={"chapter_ids": ["ch-3"]},
        )

    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Test 6 — extraction-progress returns pipeline status and per-chapter info
# ---------------------------------------------------------------------------


def test_extraction_progress_endpoint():
    """GET /textbooks/{id}/extraction-progress → returns pipeline_status and chapter list."""
    with patch("app.routers.textbooks.get_storage") as mock_get_storage:
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("partially_extracted")
        mock_store.list_chapters.return_value = CHAPTERS

        resp = client.get(f"/api/textbooks/{TEXTBOOK_ID}/extraction-progress")

    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_status"] == "partially_extracted"
    assert "chapters" in data
    assert len(data["chapters"]) == 3
    # Verify per-chapter fields are present
    ch = data["chapters"][0]
    assert "id" in ch
    assert "title" in ch
    assert "extraction_status" in ch
