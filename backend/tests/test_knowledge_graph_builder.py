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


async def _create_section(
    store, chapter_id, section_number, title, page_start, page_end
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


def _mock_ai_router(responses_by_section, cross_section_response):
    async def _get_json_response(prompt):
        if "Concepts to analyze:" in prompt:
            return cross_section_response
        for section_title, response in responses_by_section.items():
            if f"Section: {section_title}" in prompt:
                return response
        return {"concept_groups": [], "derivations": []}

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(side_effect=_get_json_response)
    return ai_router


@pytest.mark.asyncio
async def test_build_graph_no_chapters(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id = await store.create_textbook("Test Book", "/path/test.pdf")
    job_id = await store.create_graph_job(textbook_id=textbook_id)

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    job = await store.get_graph_job(job_id)
    assert job["status"] == "failed"
    assert "No extracted chapters" in job["error"]


@pytest.mark.asyncio
async def test_build_graph_chapter_nodes_created(store, tmp_path, monkeypatch):
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
async def test_build_graph_no_ai_router(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    await _create_section(store, chapter_id, "1.1", "Vectors", 2, 5)

    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content) VALUES (?, ?, ?, ?)",
            (
                "ec-1",
                chapter_id,
                "text",
                "Vectors are quantities with magnitude and direction.",
            ),
        )
        await db.commit()

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    section_nodes = await store.get_concept_nodes(textbook_id, level="section")
    key_result_nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    assert section_nodes
    assert key_result_nodes == []


@pytest.mark.asyncio
async def test_extract_key_results_with_mock_llm(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(
        store, chapter_id, "1.1", "Critical Speeds", 5, 10
    )

    sections = [
        {
            "id": section_id,
            "title": "Critical Speeds",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {
                    "content_type": "text",
                    "content": "Energy balance describes critical speeds.",
                },
                {
                    "content_type": "equation",
                    "content": "T = \\frac{{1}}{{2}}\\sum m_i \\omega_c^2 y_i^2",
                },
            ],
        }
    ]

    response = {
        "concept_groups": [
            {
                "name": "Critical Speed Analysis",
                "description": "Methods for estimating shaft critical speed",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Rayleigh's Method",
                        "node_type": "method",
                        "defining_equation": "T = \\frac{1}{2}\\sum m_i \\omega_c^2 y_i^2",
                        "description": "Energy-based method for estimating critical speed",
                    },
                    {
                        "title": "Critical Speed Formula",
                        "node_type": "formula",
                        "defining_equation": "\\frac{1}{\\omega_c^2} = \\frac{1}{\\omega_1^2} + \\frac{1}{\\omega_2^2}",
                        "description": "Dunkerley's approximation for critical speed",
                    },
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [
            {
                "source": "Rayleigh's Method",
                "target": "Critical Speed Formula",
                "description": "Energy balance leads to frequency relationship",
                "derivation_steps": [
                    "T_{max} = V_{max}",
                    "\\omega_c^2 = \\sum k_i y_i^2 / \\sum m_i y_i^2",
                ],
            }
        ],
    }
    ai_router = _mock_ai_router({"Critical Speeds": response}, {"relationships": []})
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    titles = {node["title"] for node in nodes}
    assert {"Rayleigh's Method", "Critical Speed Formula"}.issubset(titles)

    edges = await store.get_concept_edges(textbook_id)
    derives_edges = [
        edge for edge in edges if edge["relationship_type"] == "derives_from"
    ]
    assert len(derives_edges) == 1


@pytest.mark.asyncio
async def test_key_result_nodes_have_defining_equation(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(store, chapter_id, "1.1", "Formulas", 5, 10)

    sections = [
        {
            "id": section_id,
            "title": "Formulas",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Key formulas."},
            ],
        }
    ]

    response = {
        "concept_groups": [
            {
                "name": "Critical Speed Formulas",
                "description": "Key formulas for critical speed analysis",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Critical Speed Formula",
                        "node_type": "formula",
                        "defining_equation": "\\frac{1}{\\omega_c^2} = \\frac{1}{\\omega_1^2}",
                        "description": "Approximation for critical speed",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }
    ai_router = _mock_ai_router({"Formulas": response}, {"relationships": []})
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="subsection")
    assert nodes
    member_node = next(
        (n for n in nodes if n["title"] == "Critical Speed Formula"), None
    )
    assert member_node
    metadata = json.loads(member_node["metadata_json"])
    assert (
        metadata["defining_equation"]
        == "\\frac{1}{\\omega_c^2} = \\frac{1}{\\omega_1^2}"
    )


@pytest.mark.asyncio
async def test_derivation_edges_have_steps(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(store, chapter_id, "1.1", "Derivations", 5, 10)

    sections = [
        {
            "id": section_id,
            "title": "Derivations",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Derivation steps."},
            ],
        }
    ]

    response = {
        "concept_groups": [
            {
                "name": "Derivation Methods",
                "description": "Methods and formulas with derivation relationships",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Rayleigh's Method",
                        "node_type": "method",
                        "defining_equation": "T = \\frac{1}{2}\\sum m_i \\omega_c^2 y_i^2",
                        "description": "Energy-based method",
                    },
                    {
                        "title": "Critical Speed Formula",
                        "node_type": "formula",
                        "defining_equation": "\\frac{1}{\\omega_c^2} = \\frac{1}{\\omega_1^2}",
                        "description": "Approximation for critical speed",
                    },
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [
            {
                "source": "Rayleigh's Method",
                "target": "Critical Speed Formula",
                "description": "Energy balance leads to formula",
                "derivation_steps": ["T_{max} = V_{max}"],
            }
        ],
    }
    ai_router = _mock_ai_router({"Derivations": response}, {"relationships": []})
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    edges = await store.get_concept_edges(textbook_id)
    derives_edges = [
        edge for edge in edges if edge["relationship_type"] == "derives_from"
    ]
    assert derives_edges
    metadata = json.loads(derives_edges[0]["metadata_json"])
    assert metadata["derivation_steps"] == ["T_{max} = V_{max}"]


@pytest.mark.asyncio
async def test_deduplication_across_sections(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id_a = await _create_section(
        store, chapter_id, "1.1", "Rotating Machinery", 5, 10
    )
    section_id_b = await _create_section(store, chapter_id, "1.2", "Shafts", 11, 15)

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

    response = {
        "concept_groups": [
            {
                "name": "Critical Speed Concepts",
                "description": "Core concepts related to critical speed",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Critical Speed",
                        "node_type": "concept",
                        "defining_equation": "",
                        "description": "Rotation frequency leading to resonance.",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }
    ai_router = _mock_ai_router(
        {"Rotating Machinery": response, "Shafts": response}, {"relationships": []}
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
async def test_cross_section_relationships(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(
        store, chapter_id, "1.1", "Critical Speeds", 5, 10
    )

    sections = [
        {
            "id": section_id,
            "title": "Critical Speeds",
            "chapter_id": chapter_id,
            "page_start": 5,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Energy balance method."},
            ],
        }
    ]

    response = {
        "concept_groups": [
            {
                "name": "Critical Speed Analysis",
                "description": "Methods for estimating shaft critical speed",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Rayleigh's Method",
                        "node_type": "method",
                        "defining_equation": "T = \\frac{1}{2}\\sum m_i \\omega_c^2 y_i^2",
                        "description": "Energy-based method",
                    },
                    {
                        "title": "Critical Speed Formula",
                        "node_type": "formula",
                        "defining_equation": "\\frac{1}{\\omega_c^2} = \\frac{1}{\\omega_1^2}",
                        "description": "Approximation for critical speed",
                    },
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }
    relationships = {
        "relationships": [
            {
                "source": "Rayleigh's Method",
                "target": "Critical Speed Formula",
                "relationship_type": "uses",
                "confidence": 0.9,
                "reasoning": "Uses Rayleigh method to derive formula",
            }
        ]
    }
    ai_router = _mock_ai_router({"Critical Speeds": response}, relationships)
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    edges = await store.get_concept_edges(textbook_id)
    uses_edges = [edge for edge in edges if edge["relationship_type"] == "uses"]
    assert uses_edges


@pytest.mark.asyncio
async def test_no_equation_nodes_created(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    await _create_section(store, chapter_id, "1.1", "Equations", 10, 20)

    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "INSERT INTO extracted_content (id, chapter_id, content_type, content, page_number, order_index) VALUES (?, ?, ?, ?, ?, ?)",
            ("eq-1", chapter_id, "equation", "F = m a", 12, 1),
        )
        await db.commit()

    builder = KnowledgeGraphBuilder(store)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id, level="equation")
    assert nodes == []


@pytest.mark.asyncio
async def test_no_shared_variables_edges(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(store, chapter_id, "1.1", "Resonance", 10, 20)

    sections = [
        {
            "id": section_id,
            "title": "Resonance",
            "chapter_id": chapter_id,
            "page_start": 10,
            "page_end": 20,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Resonance basics."},
                {"content_type": "equation", "content": "\\omega_c = 2 \\pi f"},
            ],
        }
    ]

    response = {
        "concept_groups": [
            {
                "name": "Resonance Concepts",
                "description": "Core concepts related to resonance",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Critical Speed",
                        "node_type": "concept",
                        "defining_equation": "\\omega_c = 2 \\pi f",
                        "description": "Rotation frequency leading to resonance.",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }
    ai_router = _mock_ai_router({"Resonance": response}, {"relationships": []})
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    edges = await store.get_concept_edges(textbook_id)
    shared_edges = [
        edge for edge in edges if edge["relationship_type"] == "shared_variables"
    ]
    assert shared_edges == []
