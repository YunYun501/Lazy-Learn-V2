"""Tests for the /api/courses CRUD router."""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MATH_LIBRARY_NAME = "Math Library"


def unique_name(prefix: str = "Test Course") -> str:
    """Generate a unique course name to avoid test isolation issues."""
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def find_math_library(courses: list) -> dict:
    """Find the Math Library course in a list of courses."""
    for c in courses:
        if c['name'] == MATH_LIBRARY_NAME:
            return c
    return None


# ---------------------------------------------------------------------------
# Helper: create a course and return the response JSON
# ---------------------------------------------------------------------------

def create_course(name: str) -> dict:
    resp = client.post("/api/courses/", json={"name": name})
    assert resp.status_code == 200, resp.json()
    return resp.json()


def delete_course(course_id: str):
    client.delete(f"/api/courses/{course_id}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_course():
    """POST /api/courses/ returns 200 with id and name."""
    name = unique_name()
    resp = client.post("/api/courses/", json={"name": name})
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["name"] == name
    # Cleanup
    delete_course(data["id"])


def test_create_course_duplicate_name():
    """POST same name twice → 409 on second call."""
    name = unique_name()
    first = create_course(name)
    try:
        resp = client.post("/api/courses/", json={"name": name})
        assert resp.status_code == 409
    finally:
        delete_course(first["id"])


def test_list_courses_includes_math_library():
    """GET /api/courses/ returns a list that includes Math Library."""
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    courses = resp.json()
    assert isinstance(courses, list)
    math_lib = find_math_library(courses)
    assert math_lib is not None, "Math Library should always be present"
    assert "textbook_count" in math_lib
    assert "material_count" in math_lib


def test_get_course():
    """Create then GET by id → correct data with counts."""
    name = unique_name()
    created = create_course(name)
    course_id = created["id"]
    try:
        resp = client.get(f"/api/courses/{course_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == course_id
        assert data["name"] == name
        assert "created_at" in data
        assert data["textbook_count"] == 0
        assert data["material_count"] == 0
    finally:
        delete_course(course_id)


def test_get_course_not_found():
    """GET nonexistent id → 404."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/courses/{fake_id}")
    assert resp.status_code == 404


def test_update_course():
    """PUT with new name → 200, name changed."""
    name = unique_name("Before")
    new_name = unique_name("After")
    created = create_course(name)
    course_id = created["id"]
    try:
        resp = client.put(f"/api/courses/{course_id}", json={"name": new_name})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == new_name
    finally:
        delete_course(course_id)


def test_update_course_math_library_blocked():
    """PUT on Math Library course → 403."""
    # Get Math Library id
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    math_lib = find_math_library(resp.json())
    assert math_lib is not None
    ml_id = math_lib["id"]

    resp = client.put(f"/api/courses/{ml_id}", json={"name": "Renamed Library"})
    assert resp.status_code == 403
    assert "Math Library" in resp.json()["detail"]


def test_delete_course():
    """DELETE created course → 200, then GET → 404."""
    name = unique_name()
    created = create_course(name)
    course_id = created["id"]

    del_resp = client.delete(f"/api/courses/{course_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Course deleted successfully"

    get_resp = client.get(f"/api/courses/{course_id}")
    assert get_resp.status_code == 404


def test_delete_math_library_blocked():
    """DELETE Math Library course → 403."""
    resp = client.get("/api/courses/")
    assert resp.status_code == 200
    math_lib = find_math_library(resp.json())
    assert math_lib is not None
    ml_id = math_lib["id"]

    resp = client.delete(f"/api/courses/{ml_id}")
    assert resp.status_code == 403
    assert "Math Library" in resp.json()["detail"]
