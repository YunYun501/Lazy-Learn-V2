"""Tests for the material upload pipeline (TDD — tests written first).

Tests verify that:
1. Uploading a material triggers MaterialSummarizer in a background task.
2. When the course has textbooks, RetroactiveMatcher runs after summarization.
3. When the course has no textbooks, RetroactiveMatcher is NOT called.
4. The upload response returns the material record (including material_id).
"""
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COURSE_ID = "course-test-123"
MATERIAL_ID = "material-test-456"

MATERIAL_RECORD = {
    "id": MATERIAL_ID,
    "course_id": COURSE_ID,
    "title": "test.pdf",
    "file_type": "pdf",
    "filepath": f"/fake/path/{MATERIAL_ID}_test.pdf",
    "created_at": "2024-01-01T00:00:00",
}

QUALIFYING_TEXTBOOK = {
    "id": "tb-001",
    "title": "Intro to CS",
    "pipeline_status": "toc_extracted",
    "course_id": COURSE_ID,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(textbooks=None):
    """Return a fully mocked MetadataStore with all methods the upload pipeline needs."""
    store = MagicMock()
    store.initialize = AsyncMock()
    store.get_course = AsyncMock(return_value={"id": COURSE_ID, "name": "Test Course"})
    store.create_university_material = AsyncMock(return_value=MATERIAL_RECORD)
    store.get_course_textbooks = AsyncMock(
        return_value=textbooks if textbooks is not None else []
    )
    return store


def _make_summarizer_cls():
    """Return a mocked MaterialSummarizer class and its pre-configured instance."""
    instance = MagicMock()
    instance.summarize = AsyncMock()
    cls = MagicMock(return_value=instance)
    return cls, instance


def _make_retro_cls():
    """Return a mocked RetroactiveMatcher class and its pre-configured instance."""
    instance = MagicMock()
    instance.on_material_summarized = AsyncMock(return_value={})
    cls = MagicMock(return_value=instance)
    return cls, instance


@pytest.fixture
def test_pdf(tmp_path):
    """Create a minimal test PDF file for upload."""
    f = tmp_path / "test.pdf"
    f.write_bytes(b"%PDF-1.4 minimal test content")
    return f


def _upload(test_pdf, tmp_path, mock_store, mock_summarizer_cls, mock_retro_cls):
    """Execute the upload POST with all service dependencies mocked.

    Uses ExitStack so all patches remain active during background task execution
    (TestClient runs background tasks synchronously within the request lifecycle).
    """
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.university_materials.get_storage", return_value=mock_store)
        )
        stack.enter_context(
            patch("app.routers.university_materials.MaterialSummarizer", mock_summarizer_cls)
        )
        stack.enter_context(
            patch("app.routers.university_materials.RetroactiveMatcher", mock_retro_cls)
        )
        stack.enter_context(patch("app.routers.university_materials.RelevanceMatcher"))
        stack.enter_context(patch("app.routers.university_materials.AIRouter"))
        stack.enter_context(
            patch(
                "app.routers.university_materials.get_deepseek_api_key",
                new=AsyncMock(return_value="sk-test-key"),
            )
        )
        mock_settings = stack.enter_context(
            patch("app.routers.university_materials.settings")
        )
        mock_settings.DATA_DIR = tmp_path
        mock_settings.OPENAI_API_KEY = ""

        with open(test_pdf, "rb") as fh:
            return client.post(
                "/api/university-materials/upload",
                data={"course_id": COURSE_ID},
                files={"file": ("test.pdf", fh, "application/pdf")},
            )


# ---------------------------------------------------------------------------
# Test 1 — upload triggers summarization
# ---------------------------------------------------------------------------


def test_upload_triggers_summarization(test_pdf, tmp_path):
    """POST upload → material saved + MaterialSummarizer.summarize called in background."""
    mock_store = _make_store(textbooks=[])
    mock_summarizer_cls, mock_summarizer_instance = _make_summarizer_cls()
    mock_retro_cls, _ = _make_retro_cls()

    resp = _upload(test_pdf, tmp_path, mock_store, mock_summarizer_cls, mock_retro_cls)

    assert resp.status_code == 200
    mock_summarizer_instance.summarize.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2 — upload with textbooks triggers retroactive matching
# ---------------------------------------------------------------------------


def test_upload_with_textbooks_triggers_matching(test_pdf, tmp_path):
    """Course has textbooks → RetroactiveMatcher.on_material_summarized called after summarization."""
    mock_store = _make_store(textbooks=[QUALIFYING_TEXTBOOK])
    mock_summarizer_cls, mock_summarizer_instance = _make_summarizer_cls()
    mock_retro_cls, mock_retro_instance = _make_retro_cls()

    resp = _upload(test_pdf, tmp_path, mock_store, mock_summarizer_cls, mock_retro_cls)

    assert resp.status_code == 200
    mock_summarizer_instance.summarize.assert_called_once()
    mock_retro_instance.on_material_summarized.assert_called_once_with(COURSE_ID)


# ---------------------------------------------------------------------------
# Test 3 — upload without textbooks → no retroactive matching
# ---------------------------------------------------------------------------


def test_upload_without_textbooks_no_matching(test_pdf, tmp_path):
    """Empty course → summarization runs but RetroactiveMatcher is NOT called."""
    mock_store = _make_store(textbooks=[])
    mock_summarizer_cls, mock_summarizer_instance = _make_summarizer_cls()
    mock_retro_cls, mock_retro_instance = _make_retro_cls()

    resp = _upload(test_pdf, tmp_path, mock_store, mock_summarizer_cls, mock_retro_cls)

    assert resp.status_code == 200
    mock_summarizer_instance.summarize.assert_called_once()
    mock_retro_instance.on_material_summarized.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4 — response includes material_id (summary is async, not in response)
# ---------------------------------------------------------------------------


def test_summary_returned_in_response(test_pdf, tmp_path):
    """Upload response contains material_id; summary happens in background, not in the response body."""
    mock_store = _make_store(textbooks=[])
    mock_summarizer_cls, _ = _make_summarizer_cls()
    mock_retro_cls, _ = _make_retro_cls()

    resp = _upload(test_pdf, tmp_path, mock_store, mock_summarizer_cls, mock_retro_cls)

    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["id"] == MATERIAL_ID
