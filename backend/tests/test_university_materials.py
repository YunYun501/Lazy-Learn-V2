import asyncio
import pytest
from fastapi.testclient import TestClient

import app.routers.university_materials as um_router
from app.main import app
from app.services.storage import MetadataStore


@pytest.fixture
def client_with_course(tmp_path, monkeypatch):
    """TestClient backed by a temp DB with a pre-created course."""
    db_path = tmp_path / "test.db"

    # Pre-create course synchronously before TestClient starts
    store = MetadataStore(db_path=db_path)

    async def _setup():
        await store.initialize()
        return await store.create_course("Test Course")

    course_id = asyncio.get_event_loop().run_until_complete(_setup())

    # Patch get_storage in the router to use temp DB
    def mock_get_storage():
        return MetadataStore(db_path=db_path)

    monkeypatch.setattr(um_router, "get_storage", mock_get_storage)

    # Patch settings.DATA_DIR so files go into tmp_path
    class FakeSettings:
        DATA_DIR = tmp_path

    monkeypatch.setattr(um_router, "settings", FakeSettings)

    with TestClient(app) as c:
        yield c, course_id


def test_upload_valid_file(client_with_course):
    """Upload a PDF to a valid course → 200 + metadata returned."""
    client, course_id = client_with_course

    response = client.post(
        "/api/university-materials/upload",
        data={"course_id": course_id},
        files={"file": ("test.pdf", b"fake pdf content", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["course_id"] == course_id
    assert body["title"] == "test.pdf"
    assert body["file_type"] == "pdf"
    assert "id" in body
    assert "created_at" in body


def test_upload_invalid_extension(client_with_course):
    """Upload .exe file → 400 with error message."""
    client, course_id = client_with_course

    response = client.post(
        "/api/university-materials/upload",
        data={"course_id": course_id},
        files={"file": ("malware.exe", b"bad content", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_invalid_course_id(client_with_course):
    """Upload to nonexistent course → 404."""
    client, _ = client_with_course

    response = client.post(
        "/api/university-materials/upload",
        data={"course_id": "00000000-0000-0000-0000-000000000000"},
        files={"file": ("notes.pdf", b"content", "application/pdf")},
    )
    assert response.status_code == 404
    assert "Course not found" in response.json()["detail"]


def test_list_materials(client_with_course):
    """Upload a file then GET → returned list includes it."""
    client, course_id = client_with_course

    client.post(
        "/api/university-materials/upload",
        data={"course_id": course_id},
        files={"file": ("lecture.pdf", b"slide data", "application/pdf")},
    )

    response = client.get(f"/api/university-materials?course_id={course_id}")
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 1
    assert materials[0]["title"] == "lecture.pdf"


def test_delete_material(client_with_course):
    """Upload, DELETE, then GET → empty list."""
    client, course_id = client_with_course

    upload = client.post(
        "/api/university-materials/upload",
        data={"course_id": course_id},
        files={"file": ("slides.pptx", b"pptx data", "application/vnd.ms-powerpoint")},
    )
    assert upload.status_code == 200
    material_id = upload.json()["id"]

    delete_resp = client.delete(f"/api/university-materials/{material_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["message"] == "Deleted"

    list_resp = client.get(f"/api/university-materials?course_id={course_id}")
    assert list_resp.json() == []
