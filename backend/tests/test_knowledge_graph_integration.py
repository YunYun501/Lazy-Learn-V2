"""
Integration tests for the full knowledge graph pipeline:
build → status → graph → node detail → delete
Uses TestClient with patched storage (no real LLM or DB path).
"""

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.storage import MetadataStore

client = TestClient(app)


def _make_store(tmp_path_str: str) -> tuple[MetadataStore, str]:
    db_path = Path(tmp_path_str) / "integration.db"
    store = MetadataStore(db_path)
    asyncio.run(store.initialize())
    return store


def test_build_endpoint_creates_job(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        await store.update_textbook_pipeline_status(tb_id, "fully_extracted")
        await store.create_chapter(tb_id, "1", "Ch1", 1, 10)
        return tb_id

    textbook_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.post(f"/api/knowledge-graph/{textbook_id}/build")

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["textbook_id"] == textbook_id
    assert data["status"] == "pending"


def test_build_rejects_non_extracted_textbook(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        return tb_id

    textbook_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.post(f"/api/knowledge-graph/{textbook_id}/build")

    assert response.status_code == 400


def test_status_returns_completed_job(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        job_id = await store.create_graph_job(tb_id, total_chapters=2)
        await store.update_graph_job(
            job_id=job_id, status="completed", progress_pct=1.0, processed_chapters=2
        )
        return tb_id

    textbook_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.get(f"/api/knowledge-graph/{textbook_id}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["textbook_id"] == textbook_id
    assert data["progress_pct"] == 1.0


def test_graph_endpoint_returns_nodes_and_edges(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        node1 = await store.create_concept_node(
            tb_id, "Theorem A", "theorem", "chapter"
        )
        node2 = await store.create_concept_node(tb_id, "Lemma B", "lemma", "section")
        await store.create_concept_edge(tb_id, node1, node2, "proves")
        return tb_id

    textbook_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.get(f"/api/knowledge-graph/{textbook_id}/graph")

    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0]["relationship_type"] == "proves"
    titles = {n["title"] for n in data["nodes"]}
    assert "Theorem A" in titles
    assert "Lemma B" in titles


def test_node_detail_returns_edges(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        node1 = await store.create_concept_node(
            tb_id, "Theorem A", "theorem", "chapter"
        )
        node2 = await store.create_concept_node(tb_id, "Lemma B", "lemma", "section")
        await store.create_concept_edge(tb_id, node1, node2, "proves")
        return tb_id, node1

    textbook_id, node_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.get(f"/api/knowledge-graph/{textbook_id}/node/{node_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["node"]["id"] == node_id
    assert data["node"]["title"] == "Theorem A"
    assert len(data["outgoing_edges"]) == 1
    assert data["outgoing_edges"][0]["relationship_type"] == "proves"


def test_delete_clears_graph(tmp_path):
    store = _make_store(str(tmp_path))

    async def seed():
        tb_id = await store.create_textbook("Test Book", "t.pdf")
        await store.create_concept_node(tb_id, "Node A", "theorem", "chapter")
        await store.create_concept_node(tb_id, "Node B", "definition", "section")
        return tb_id

    textbook_id = asyncio.run(seed())

    with patch("app.routers.knowledge_graph.get_storage", return_value=store):
        response = client.delete(f"/api/knowledge-graph/{textbook_id}")

    assert response.status_code == 204

    async def check():
        nodes = await store.get_concept_nodes(textbook_id)
        return nodes

    remaining = asyncio.run(check())
    assert len(remaining) == 0
