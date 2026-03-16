import json
from unittest.mock import AsyncMock

import aiosqlite
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
    await store.update_chapter_extraction_status(chapter_id, "extracted")
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

    import aiosqlite

    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content) VALUES (?, ?, ?, ?)",
            (
                "ec-1",
                chapter_id,
                "text",
                "Vectors are quantities with magnitude and direction. Scalars have only magnitude.",
            ),
        )
        await db.commit()

    concepts_response = {
        "concepts": [
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
    }
    relationships_response = {"relationships": []}
    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(
        side_effect=[concepts_response, relationships_response]
    )

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


@pytest.mark.asyncio
async def test_per_section_extraction(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    section_id_a = await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.1",
            "title": "Kinematics",
            "page_start": 5,
            "page_end": 10,
            "parent_section_id": None,
            "level": 2,
        }
    )
    section_id_b = await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.2",
            "title": "Dynamics",
            "page_start": 11,
            "page_end": 15,
            "parent_section_id": None,
            "level": 2,
        }
    )

    sections = [
        {
            "id": section_id_a,
            "title": "Kinematics",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {
                    "content_type": "text",
                    "content": "Angular velocity describes rotation.",
                },
                {"content_type": "equation", "content": "\\omega = v / r"},
            ],
        },
        {
            "id": section_id_b,
            "title": "Dynamics",
            "chapter_id": chapter_id,
            "page_start": 11,
            "page_end": 15,
            "section_number": "1.2",
            "section_path": "CH1/1.2",
            "content_entries": [
                {"content_type": "text", "content": "Torque causes angular accel."},
                {"content_type": "equation", "content": "\\tau = I \\alpha"},
            ],
        },
    ]

    concepts_a = {
        "concepts": [
            {
                "title": "Angular Velocity",
                "node_type": "concept",
                "description": "Rate of change of angle.",
                "aliases": [],
                "prerequisites": [],
            }
        ],
        "section_relationships": [],
    }
    concepts_b = {
        "concepts": [
            {
                "title": "Torque",
                "node_type": "definition",
                "description": "Moment causing rotation.",
                "aliases": [],
                "prerequisites": [],
            }
        ],
        "section_relationships": [],
    }

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(
        side_effect=[concepts_a, concepts_b, {"relationships": []}]
    )
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    titles = {node["title"] for node in nodes}
    assert {"Angular Velocity", "Torque"}.issubset(titles)


@pytest.mark.asyncio
async def test_equation_node_creation(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.1",
            "title": "Equations",
            "page_start": 10,
            "page_end": 20,
            "parent_section_id": None,
            "level": 2,
        }
    )

    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            ("eq-1", chapter_id, "equation", "F = m a", 12, 1),
        )
        await db.commit()

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="equation")
    assert len(nodes) == 1
    metadata = json.loads(nodes[0]["metadata_json"])
    assert "variables" in metadata
    assert "raw_latex" in metadata
    assert "m" in metadata["variables"]


@pytest.mark.asyncio
async def test_variable_cooccurrence_edges(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.1",
            "title": "Resonance",
            "page_start": 10,
            "page_end": 20,
            "parent_section_id": None,
            "level": 2,
        }
    )

    async with aiosqlite.connect(store.db_path) as db:
        await db.executemany(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("eq-1", chapter_id, "equation", "\\omega_{c} = 2 \\pi f", 12, 1),
                ("eq-2", chapter_id, "equation", "P = \\omega_{c} T", 13, 2),
                ("eq-3", chapter_id, "equation", "E = \\omega_{c}^2", 14, 3),
            ],
        )
        await db.commit()

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    edges = await store.get_concept_edges(textbook_id)
    shared_edges = [
        edge for edge in edges if edge["relationship_type"] == "shared_variables"
    ]
    assert len(shared_edges) == 3
    assert all("omega_c" in edge["reasoning"] for edge in shared_edges)


@pytest.mark.asyncio
async def test_concept_dedup_same_title(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    section_id_a = await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.1",
            "title": "Rotating Machinery",
            "page_start": 5,
            "page_end": 10,
            "parent_section_id": None,
            "level": 2,
        }
    )
    section_id_b = await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.2",
            "title": "Shafts",
            "page_start": 11,
            "page_end": 15,
            "parent_section_id": None,
            "level": 2,
        }
    )

    sections = [
        {
            "id": section_id_a,
            "title": "Rotating Machinery",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Critical speed basics."},
            ],
        },
        {
            "id": section_id_b,
            "title": "Shafts",
            "chapter_id": chapter_id,
            "page_start": 11,
            "page_end": 15,
            "section_number": "1.2",
            "section_path": "CH1/1.2",
            "content_entries": [
                {"content_type": "text", "content": "Critical speed models."},
            ],
        },
    ]

    concepts = {
        "concepts": [
            {
                "title": "Critical Speed",
                "node_type": "concept",
                "description": "Rotation frequency leading to resonance.",
                "aliases": [],
                "prerequisites": [],
            }
        ],
        "section_relationships": [],
    }

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(
        side_effect=[concepts, concepts, {"relationships": []}]
    )
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    titles = [node["title"] for node in nodes]
    assert titles.count("Critical Speed") == 1


@pytest.mark.asyncio
async def test_unparseable_equation_skipped(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": "1.1",
            "title": "Faulty Equations",
            "page_start": 10,
            "page_end": 20,
            "parent_section_id": None,
            "level": 2,
        }
    )

    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            ("eq-bad", chapter_id, "equation", None, 12, 1),
        )
        await db.commit()

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="equation")
    assert len(nodes) == 0
