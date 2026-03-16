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
        chapter_number="7",
        title="Rotordynamics",
        page_start=1,
        page_end=50,
    )
    await store.update_chapter_extraction_status(chapter_id, "extracted")
    return textbook_id, chapter_id


async def _create_section(
    store,
    chapter_id,
    section_number,
    title,
    page_start,
    page_end,
):
    return await store.create_section(
        {
            "chapter_id": chapter_id,
            "section_number": section_number,
            "title": title,
            "page_start": page_start,
            "page_end": page_end,
            "parent_section_id": None,
            "level": 2,
        }
    )


async def _seed_sections(store, chapter_id):
    section_id_a = await _create_section(
        store=store,
        chapter_id=chapter_id,
        section_number="7.1",
        title="Critical Speeds",
        page_start=10,
        page_end=20,
    )
    section_id_b = await _create_section(
        store=store,
        chapter_id=chapter_id,
        section_number="7.2",
        title="Balancing",
        page_start=21,
        page_end=30,
    )
    return section_id_a, section_id_b


async def _seed_extracted_content(store, chapter_id):
    entries = [
        (
            "text-1",
            chapter_id,
            "text",
            "Critical speed is the rotational speed where resonance occurs.",
            11,
            1,
        ),
        (
            "eq-1",
            chapter_id,
            "equation",
            "$$\\omega_{c} = \\sqrt{g/y}$$",
            12,
            2,
        ),
        (
            "text-2",
            chapter_id,
            "text",
            "Resonance amplifies vibration near critical speed.",
            15,
            3,
        ),
        (
            "eq-2",
            chapter_id,
            "equation",
            "$$\\frac{1}{\\omega_{c}^{2}} = \\frac{1}{\\omega_{1}^{2}}$$",
            18,
            4,
        ),
        (
            "text-3",
            chapter_id,
            "text",
            "Balancing reduces vibration and improves stability.",
            22,
            5,
        ),
        (
            "eq-3",
            chapter_id,
            "equation",
            "$$F = m a$$",
            24,
            6,
        ),
    ]
    async with aiosqlite.connect(store.db_path) as db:
        await db.executemany(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            entries,
        )
        await db.commit()


def _mock_ai_router(chapter_concepts, section_concepts, relationships):
    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(
        side_effect=[chapter_concepts, *section_concepts, relationships]
    )
    return ai_router


async def _run_builder(
    store,
    tmp_path,
    monkeypatch,
    chapter_concepts,
    section_concepts,
    relationships,
):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    await _seed_sections(store, chapter_id)
    await _seed_extracted_content(store, chapter_id)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    ai_router = _mock_ai_router(chapter_concepts, section_concepts, relationships)
    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)
    return textbook_id


@pytest.mark.asyncio
async def test_full_pipeline_creates_four_levels(store, tmp_path, monkeypatch):
    chapter_concepts = {
        "concepts": [
            {
                "title": "Shaft Design",
                "node_type": "concept",
                "description": "Design considerations for rotating shafts.",
                "aliases": [],
            }
        ]
    }
    section_concepts = [
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Speed at which resonance occurs.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [
                {
                    "source": "Critical Speed",
                    "target": "Resonance",
                    "relationship_type": "uses",
                    "reasoning": "Critical speed analysis relies on resonance.",
                }
            ],
        },
        {
            "concepts": [
                {
                    "title": "Resonance",
                    "node_type": "concept",
                    "description": "Large amplitude response near natural frequency.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
    ]
    relationships = {
        "relationships": [
            {
                "source": "Shaft Design",
                "target": "Critical Speed",
                "relationship_type": "uses",
                "confidence": 0.9,
                "reasoning": "Design depends on critical speed calculations.",
            }
        ]
    }

    textbook_id = await _run_builder(
        store,
        tmp_path,
        monkeypatch,
        chapter_concepts,
        section_concepts,
        relationships,
    )

    chapter_nodes = await store.get_concept_nodes(textbook_id, level="chapter")
    section_nodes = await store.get_concept_nodes(textbook_id, level="section")
    subsection_nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    equation_nodes = await store.get_concept_nodes(textbook_id, level="equation")
    all_nodes = await store.get_concept_nodes(textbook_id)

    assert chapter_nodes
    assert section_nodes
    assert subsection_nodes
    assert equation_nodes
    assert len(all_nodes) >= 8


@pytest.mark.asyncio
async def test_shared_variables_edges_created(store, tmp_path, monkeypatch):
    chapter_concepts = {
        "concepts": [
            {
                "title": "Shaft Design",
                "node_type": "concept",
                "description": "Design considerations for rotating shafts.",
                "aliases": [],
            }
        ]
    }
    section_concepts = [
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Speed at which resonance occurs.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
        {
            "concepts": [
                {
                    "title": "Balancing",
                    "node_type": "concept",
                    "description": "Mass distribution to reduce vibration.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
    ]
    relationships = {"relationships": []}

    textbook_id = await _run_builder(
        store,
        tmp_path,
        monkeypatch,
        chapter_concepts,
        section_concepts,
        relationships,
    )

    edges = await store.get_concept_edges(textbook_id)
    shared_edges = [
        edge for edge in edges if edge["relationship_type"] == "shared_variables"
    ]
    equation_nodes = await store.get_concept_nodes(textbook_id, level="equation")
    equation_ids = {node["id"] for node in equation_nodes}

    assert shared_edges
    assert all(edge["source_node_id"] in equation_ids for edge in shared_edges)
    assert all(edge["target_node_id"] in equation_ids for edge in shared_edges)


@pytest.mark.asyncio
async def test_concept_dedup_across_sections(store, tmp_path, monkeypatch):
    chapter_concepts = {
        "concepts": [
            {
                "title": "Shaft Design",
                "node_type": "concept",
                "description": "Design considerations for rotating shafts.",
                "aliases": [],
            }
        ]
    }
    section_concepts = [
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Speed at which resonance occurs.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Shared concept across sections.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
    ]
    relationships = {"relationships": []}

    textbook_id = await _run_builder(
        store,
        tmp_path,
        monkeypatch,
        chapter_concepts,
        section_concepts,
        relationships,
    )

    nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    titles = [node["title"] for node in nodes]
    assert titles.count("Critical Speed") == 1


@pytest.mark.asyncio
async def test_equation_nodes_have_metadata(store, tmp_path, monkeypatch):
    chapter_concepts = {
        "concepts": [
            {
                "title": "Shaft Design",
                "node_type": "concept",
                "description": "Design considerations for rotating shafts.",
                "aliases": [],
            }
        ]
    }
    section_concepts = [
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Speed at which resonance occurs.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
        {
            "concepts": [
                {
                    "title": "Balancing",
                    "node_type": "concept",
                    "description": "Mass distribution to reduce vibration.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
    ]
    relationships = {"relationships": []}

    textbook_id = await _run_builder(
        store,
        tmp_path,
        monkeypatch,
        chapter_concepts,
        section_concepts,
        relationships,
    )

    nodes = await store.get_concept_nodes(textbook_id, level="equation")
    assert nodes
    for node in nodes:
        assert node["metadata_json"]
        metadata = json.loads(node["metadata_json"])
        assert isinstance(metadata.get("variables"), list)
        assert isinstance(metadata.get("raw_latex"), str)


@pytest.mark.asyncio
async def test_contains_edges_link_hierarchy(store, tmp_path, monkeypatch):
    chapter_concepts = {
        "concepts": [
            {
                "title": "Shaft Design",
                "node_type": "concept",
                "description": "Design considerations for rotating shafts.",
                "aliases": [],
            }
        ]
    }
    section_concepts = [
        {
            "concepts": [
                {
                    "title": "Critical Speed",
                    "node_type": "theorem",
                    "description": "Speed at which resonance occurs.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
        {
            "concepts": [
                {
                    "title": "Balancing",
                    "node_type": "concept",
                    "description": "Mass distribution to reduce vibration.",
                    "aliases": [],
                    "prerequisites": [],
                }
            ],
            "section_relationships": [],
        },
    ]
    relationships = {"relationships": []}

    textbook_id = await _run_builder(
        store,
        tmp_path,
        monkeypatch,
        chapter_concepts,
        section_concepts,
        relationships,
    )

    edges = await store.get_concept_edges(textbook_id)
    contains_edges = [edge for edge in edges if edge["relationship_type"] == "contains"]
    nodes = await store.get_concept_nodes(textbook_id)
    nodes_by_id = {node["id"]: node for node in nodes}

    assert contains_edges
    for edge in contains_edges:
        source = nodes_by_id[edge["source_node_id"]]
        target = nodes_by_id[edge["target_node_id"]]
        assert source["level"] in {"section", "chapter"}
        assert target["level"] in {"equation", "subsection", "section", "chapter"}
