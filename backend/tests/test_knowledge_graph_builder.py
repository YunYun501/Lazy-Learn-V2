import json
from unittest.mock import AsyncMock

import pytest

from app.services.knowledge_graph_builder import KnowledgeGraphBuilder
from app.services.storage import MetadataStore


@pytest.fixture
async def store(tmp_path):
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store


async def _seed_textbook_and_chapter(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    chapter_id = await store.create_chapter(
        textbook_id=textbook_id,
        chapter_number="1",
        title="Introduction",
        page_start=1,
        page_end=10,
    )
    return textbook_id, chapter_id


@pytest.mark.asyncio
async def test_build_graph_creates_chapter_nodes(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="chapter")
    assert len(nodes) == 1
    assert nodes[0]["title"] == "Introduction"
    assert nodes[0]["source_chapter_id"] == chapter_id


@pytest.mark.asyncio
async def test_build_graph_marks_job_completed(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    job = await store.get_graph_job(job_id)
    assert job["status"] == "completed"
    assert job["progress_pct"] == 1.0
    assert job["completed_at"] is not None


@pytest.mark.asyncio
async def test_build_graph_handles_missing_description(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id)
    assert len(nodes) == 1


@pytest.mark.asyncio
async def test_extract_concepts_with_mock_llm(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    desc_dir = tmp_path / "data" / "descriptions" / textbook_id
    desc_dir.mkdir(parents=True, exist_ok=True)
    (desc_dir / "chapter_1.md").write_text("Some chapter text.", encoding="utf-8")

    concepts = [
        {
            "title": "Vector",
            "node_type": "concept",
            "description": "A quantity with magnitude and direction.",
            "aliases": ["Directed quantity"],
        },
        {
            "title": "Scalar",
            "node_type": "definition",
            "description": "A magnitude without direction.",
            "aliases": [],
        },
    ]
    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(side_effect=[concepts, []])

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="section")
    titles = {node["title"] for node in nodes}
    assert {"Vector", "Scalar"}.issubset(titles)

    stored = {node["title"]: node for node in nodes}
    vector_node = stored["Vector"]
    metadata = json.loads(vector_node["metadata_json"])
    assert metadata["aliases"] == ["Directed quantity"]
    assert vector_node["source_chapter_id"] == chapter_id


@pytest.mark.asyncio
async def test_build_graph_marks_failed_on_crash(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    async def _boom(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(store, "list_chapters", _boom)
    builder = KnowledgeGraphBuilder(store)

    with pytest.raises(RuntimeError):
        await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    job = await store.get_graph_job(job_id)
    assert job["status"] == "failed"
    assert "boom" in job["error"]
