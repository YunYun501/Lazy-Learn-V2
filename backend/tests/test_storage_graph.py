import pytest
from app.services.storage import MetadataStore


@pytest.fixture
async def store(tmp_path):
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path=db_path)
    await store.initialize()
    return store


@pytest.mark.asyncio
async def test_create_and_get_concept_node(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Fourier Transform",
        node_type="theorem",
        level="chapter",
        description="Key transform definition.",
        source_chapter_id="chapter-1",
        source_section_id="section-1",
        source_page=12,
        metadata_json='{"latex": "F(k)"}',
    )

    node = await store.get_concept_node(node_id)
    assert node is not None
    assert node["id"] == node_id
    assert node["textbook_id"] == textbook_id
    assert node["title"] == "Fourier Transform"
    assert node["node_type"] == "theorem"
    assert node["level"] == "chapter"
    assert node["description"] == "Key transform definition."
    assert node["source_chapter_id"] == "chapter-1"
    assert node["source_section_id"] == "section-1"
    assert node["source_page"] == 12
    assert node["metadata_json"] == '{"latex": "F(k)"}'
    assert node["created_at"] is not None


@pytest.mark.asyncio
async def test_get_nodes_filtered_by_level(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    chapter_node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Limits",
        node_type="concept",
        level="chapter",
    )
    section_node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Epsilon-Delta",
        node_type="definition",
        level="section",
    )

    chapter_nodes = await store.get_concept_nodes(textbook_id, level="chapter")
    section_nodes = await store.get_concept_nodes(textbook_id, level="section")

    assert [node["id"] for node in chapter_nodes] == [chapter_node_id]
    assert [node["id"] for node in section_nodes] == [section_node_id]


@pytest.mark.asyncio
async def test_delete_concept_nodes_returns_count(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    for idx in range(3):
        await store.create_concept_node(
            textbook_id=textbook_id,
            title=f"Node {idx}",
            node_type="concept",
            level="section",
        )

    deleted = await store.delete_concept_nodes(textbook_id)
    assert deleted == 3
    remaining = await store.get_concept_nodes(textbook_id)
    assert remaining == []


@pytest.mark.asyncio
async def test_create_and_get_concept_edge(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    source_node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Vector Space",
        node_type="definition",
        level="chapter",
    )
    target_node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Linear Independence",
        node_type="concept",
        level="section",
    )

    edge_id = await store.create_concept_edge(
        textbook_id=textbook_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type="prerequisite_of",
        confidence=0.8,
        reasoning="Basis required first.",
    )

    edges = await store.get_concept_edges(textbook_id)
    assert len(edges) == 1
    edge = edges[0]
    assert edge["id"] == edge_id
    assert edge["textbook_id"] == textbook_id
    assert edge["source_node_id"] == source_node_id
    assert edge["target_node_id"] == target_node_id
    assert edge["relationship_type"] == "prerequisite_of"
    assert edge["confidence"] == 0.8
    assert edge["reasoning"] == "Basis required first."
    assert edge["created_at"] is not None


@pytest.mark.asyncio
async def test_graph_job_lifecycle(store):
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    job_id = await store.create_graph_job(textbook_id=textbook_id, total_chapters=4)

    job = await store.get_graph_job(job_id)
    assert job is not None
    assert job["status"] == "pending"
    assert job["progress_pct"] == 0.0
    assert job["total_chapters"] == 4
    assert job["processed_chapters"] == 0
    assert job["error"] is None

    await store.update_graph_job(
        job_id,
        status="processing",
        progress_pct=0.5,
        processed_chapters=2,
    )

    job = await store.get_graph_job(job_id)
    assert job["status"] == "processing"
    assert job["progress_pct"] == 0.5
    assert job["processed_chapters"] == 2

    await store.update_graph_job(
        job_id,
        status="completed",
        progress_pct=1.0,
        completed_at="2026-01-01T00:00:00",
    )

    job = await store.get_graph_job(job_id)
    assert job["status"] == "completed"
    assert job["progress_pct"] == 1.0
    assert job["completed_at"] == "2026-01-01T00:00:00"

    latest = await store.get_latest_graph_job(textbook_id)
    assert latest is not None
    assert latest["id"] == job_id
