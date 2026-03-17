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


def _mock_ai_router_with_enrichment(section_response, enrichment_response):
    async def _get_json_response(prompt):
        if "Concepts to analyze:" in prompt:
            return {"relationships": []}
        if (
            "Existing Knowledge Graph Nodes" in prompt
            or "equation_latex" in prompt
            or "existing_nodes_json" in prompt
        ):
            return enrichment_response
        return section_response

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(side_effect=_get_json_response)
    return ai_router


@pytest.mark.asyncio
async def test_full_pipeline_equation_node_gets_enriched(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    section_id = await _create_section(
        store, chapter_id, "13.1", "Endurance Limit", 1, 20
    )

    section_response = {
        "concept_groups": [
            {
                "name": "Fatigue Criteria",
                "description": "Fatigue design criteria",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Endurance Limit Formula",
                        "node_type": "formula",
                        "defining_equation": r"\sigma_e = k_a k_b k_c k_d k_e k_g \sigma'_e",
                        "description": "Modified endurance limit",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }
    enrichment_response = {
        "equation_components": [
            {
                "symbol": "k_a",
                "name": "surface factor",
                "type": "constant",
                "description": "Surface finish effect",
                "latex": None,
                "page_reference": "p.312",
                "linked_node_id": None,
            },
            {
                "symbol": r"\sigma'_e",
                "name": "test specimen endurance limit",
                "type": "calculated",
                "description": "Base endurance limit",
                "latex": r"\sigma'_e = 0.5 S_{ut}",
                "page_reference": None,
                "linked_node_id": None,
            },
        ]
    }

    ai_router = _mock_ai_router_with_enrichment(section_response, enrichment_response)

    sections = [
        {
            "id": section_id,
            "title": "Endurance Limit",
            "chapter_id": chapter_id,
            "page_start": 1,
            "page_end": 20,
            "section_number": "13.1",
            "section_path": "CH1/13.1",
            "content_entries": [
                {
                    "content_type": "equation",
                    "content": r"\sigma_e = k_a k_b k_c k_d k_e k_g \sigma'_e",
                }
            ],
        }
    ]
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    job_id = await store.create_graph_job(textbook_id=textbook_id)
    builder = KnowledgeGraphBuilder(store=store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id)

    enriched_nodes = []
    for node in nodes:
        metadata = json.loads(node.get("metadata_json") or "{}")
        if metadata.get("equation_components"):
            enriched_nodes.append(node)

    assert len(enriched_nodes) >= 1, "Expected at least one enriched equation node"
    components = json.loads(enriched_nodes[0]["metadata_json"])["equation_components"]
    assert len(components) == 2
    symbols = [component["symbol"] for component in components]
    assert "k_a" in symbols

    job = await store.get_graph_job(job_id)
    assert job["status"] == "completed"


@pytest.mark.asyncio
async def test_full_pipeline_no_equations_completes_gracefully(
    store, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    section_id = await _create_section(store, chapter_id, "1.1", "Introduction", 1, 10)

    section_response = {
        "concept_groups": [
            {
                "name": "Overview",
                "description": "Chapter overview",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Basic Concept",
                        "node_type": "concept",
                        "defining_equation": "",
                        "description": "A basic concept",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }

    ai_router = _mock_ai_router_with_enrichment(
        section_response, {"equation_components": []}
    )

    sections = [
        {
            "id": section_id,
            "title": "Introduction",
            "chapter_id": chapter_id,
            "page_start": 1,
            "page_end": 10,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {
                    "content_type": "text",
                    "content": "Basic concepts overview.",
                }
            ],
        }
    ]
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    job_id = await store.create_graph_job(textbook_id=textbook_id)
    builder = KnowledgeGraphBuilder(store=store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    nodes = await store.get_concept_nodes(textbook_id)

    for node in nodes:
        metadata = json.loads(node.get("metadata_json") or "{}")
        assert (
            "equation_components" not in metadata or not metadata["equation_components"]
        )

    job = await store.get_graph_job(job_id)
    assert job["status"] == "completed"
