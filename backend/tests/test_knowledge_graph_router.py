"""Tests for the knowledge graph router endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TEXTBOOK_ID = "test-textbook-kg-001"
JOB_ID = "test-job-kg-001"
NODE_ID = "test-node-kg-001"
EDGE_ID = "test-edge-kg-001"


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


def make_job(status: str = "pending") -> dict:
    return {
        "id": JOB_ID,
        "textbook_id": TEXTBOOK_ID,
        "status": status,
        "progress_pct": 0.0,
        "total_chapters": 3,
        "processed_chapters": 0,
        "error": None,
        "created_at": "2024-01-01T00:00:00",
        "completed_at": None,
    }


def make_node(node_id: str = NODE_ID) -> dict:
    return {
        "id": node_id,
        "textbook_id": TEXTBOOK_ID,
        "title": "Pythagorean Theorem",
        "description": "A fundamental theorem in geometry",
        "node_type": "theorem",
        "level": "chapter",
        "source_chapter_id": "ch-1",
        "source_section_id": None,
        "source_page": 10,
        "metadata_json": None,
        "created_at": "2024-01-01T00:00:00",
    }


def make_edge(edge_id: str = EDGE_ID) -> dict:
    return {
        "id": edge_id,
        "textbook_id": TEXTBOOK_ID,
        "source_node_id": NODE_ID,
        "target_node_id": "test-node-kg-002",
        "relationship_type": "derives_from",
        "confidence": 0.9,
        "reasoning": "Derived from basic geometry",
        "created_at": "2024-01-01T00:00:00",
    }


# ---------------------------------------------------------------------------
# Test 1 — build endpoint returns 202 for fully_extracted textbook
# ---------------------------------------------------------------------------


def test_build_endpoint_returns_202():
    """POST /api/knowledge-graph/{id}/build → 202 for fully_extracted textbook."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("fully_extracted")
        mock_store.list_chapters.return_value = [
            {"id": "ch-1"},
            {"id": "ch-2"},
            {"id": "ch-3"},
        ]
        mock_store.delete_concept_nodes.return_value = 0
        mock_store.delete_concept_edges.return_value = 0
        mock_store.create_graph_job.return_value = JOB_ID

        resp = client.post(f"/api/knowledge-graph/{TEXTBOOK_ID}/build")

    assert resp.status_code == 202
    data = resp.json()
    assert data["job_id"] == JOB_ID
    assert data["textbook_id"] == TEXTBOOK_ID
    assert data["status"] == "pending"
    assert "message" in data


# ---------------------------------------------------------------------------
# Test 2 — build endpoint rejects textbook not fully extracted
# ---------------------------------------------------------------------------


def test_build_endpoint_rejects_not_fully_extracted():
    """POST /api/knowledge-graph/{id}/build → 400 for textbook not fully_extracted."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = make_textbook("uploaded")

        resp = client.post(f"/api/knowledge-graph/{TEXTBOOK_ID}/build")

    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Test 3 — build endpoint returns 404 for missing textbook
# ---------------------------------------------------------------------------


def test_build_endpoint_returns_404_for_missing_textbook():
    """POST /api/knowledge-graph/{id}/build → 404 when textbook not found."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_textbook.return_value = None

        resp = client.post(f"/api/knowledge-graph/{TEXTBOOK_ID}/build")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 4 — status endpoint returns job data
# ---------------------------------------------------------------------------


def test_status_endpoint_returns_job():
    """GET /api/knowledge-graph/{id}/status → 200 with job data."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_latest_graph_job.return_value = make_job("processing")

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == JOB_ID
    assert data["textbook_id"] == TEXTBOOK_ID
    assert data["status"] == "processing"


# ---------------------------------------------------------------------------
# Test 5 — status endpoint returns 404 when no job exists
# ---------------------------------------------------------------------------


def test_status_endpoint_returns_404_when_no_job():
    """GET /api/knowledge-graph/{id}/status → 404 when no job exists."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_latest_graph_job.return_value = None

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/status")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 6 — graph endpoint returns nodes and edges
# ---------------------------------------------------------------------------


def test_graph_endpoint_returns_data():
    """GET /api/knowledge-graph/{id}/graph → 200 with nodes and edges."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_concept_nodes.return_value = [make_node()]
        mock_store.get_concept_edges.return_value = [make_edge()]

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/graph")

    assert resp.status_code == 200
    data = resp.json()
    assert data["textbook_id"] == TEXTBOOK_ID
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 1
    assert data["nodes"][0]["id"] == NODE_ID
    assert data["nodes"][0]["title"] == "Pythagorean Theorem"


# ---------------------------------------------------------------------------
# Test 7 — graph endpoint returns 404 when no nodes
# ---------------------------------------------------------------------------


def test_graph_endpoint_returns_404_when_no_nodes():
    """GET /api/knowledge-graph/{id}/graph → 404 when graph not generated."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_concept_nodes.return_value = []

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/graph")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 8 — node detail endpoint returns node with edges
# ---------------------------------------------------------------------------


def test_node_detail_endpoint():
    """GET /api/knowledge-graph/{id}/node/{node_id} → 200 with node and edges."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_concept_node.return_value = make_node()
        mock_store.get_concept_edges.return_value = [make_edge()]

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/node/{NODE_ID}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["node"]["id"] == NODE_ID
    assert data["node"]["title"] == "Pythagorean Theorem"
    assert isinstance(data["outgoing_edges"], list)
    assert isinstance(data["incoming_edges"], list)


# ---------------------------------------------------------------------------
# Test 9 — node detail endpoint returns 404 for missing node
# ---------------------------------------------------------------------------


def test_node_detail_returns_404_for_missing_node():
    """GET /api/knowledge-graph/{id}/node/{node_id} → 404 when node not found."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.get_concept_node.return_value = None

        resp = client.get(f"/api/knowledge-graph/{TEXTBOOK_ID}/node/{NODE_ID}")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 10 — delete endpoint returns 204
# ---------------------------------------------------------------------------


def test_delete_graph_returns_204():
    """DELETE /api/knowledge-graph/{id} → 204 No Content."""
    with (
        patch("app.routers.knowledge_graph.get_storage") as mock_get_storage,
    ):
        mock_store = AsyncMock()
        mock_get_storage.return_value = mock_store
        mock_store.delete_concept_nodes.return_value = 5
        mock_store.delete_concept_edges.return_value = 10

        resp = client.delete(f"/api/knowledge-graph/{TEXTBOOK_ID}")

    assert resp.status_code == 204
