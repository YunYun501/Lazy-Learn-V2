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


def _mock_ai_router(
    key_result_response=None,
    enrichment_response=None,
    cross_section_response=None,
    fail_enrichment=False,
):
    if key_result_response is None:
        key_result_response = {"concept_groups": [], "derivations": []}
    if enrichment_response is None:
        enrichment_response = {"equation_components": []}
    if cross_section_response is None:
        cross_section_response = {"relationships": []}

    async def _get_json_response(prompt):
        if "Concepts to analyze:" in prompt:
            return cross_section_response
        if "Existing Knowledge Graph Nodes" in prompt:
            if fail_enrichment:
                raise Exception("LLM failed")
            return enrichment_response
        if "Section:" in prompt:
            return key_result_response
        return {"concept_groups": [], "derivations": []}

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(side_effect=_get_json_response)
    return ai_router


@pytest.mark.asyncio
async def test_enrich_stores_components_in_metadata(store):
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Critical Speed Formula",
        node_type="formula",
        level="subsection",
        metadata_json=json.dumps({"defining_equation": "F = m a"}),
    )
    all_nodes = [{"id": node_id, "title": "Critical Speed Formula"}]

    ai_router = _mock_ai_router(
        enrichment_response={
            "equation_components": [
                {
                    "symbol": "m",
                    "name": "mass",
                    "type": "constant",
                    "description": "Mass of the body",
                    "latex": None,
                    "page_reference": "p.10",
                    "linked_node_id": None,
                }
            ]
        }
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder._enrich_equation_nodes(textbook_id=textbook_id, all_nodes=all_nodes)

    node = await store.get_concept_node(node_id)
    metadata = json.loads(node["metadata_json"])
    assert metadata.get("equation_components")
    assert metadata["equation_components"][0]["symbol"] == "m"


@pytest.mark.asyncio
async def test_enrich_skips_nodes_without_defining_equation(store):
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="No Equation",
        node_type="concept",
        level="subsection",
        metadata_json=json.dumps({}),
    )
    all_nodes = [{"id": node_id, "title": "No Equation"}]

    ai_router = _mock_ai_router()
    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder._enrich_equation_nodes(textbook_id=textbook_id, all_nodes=all_nodes)

    ai_router.get_json_response.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_llm_failure_is_silent(store):
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Equation Node",
        node_type="formula",
        level="subsection",
        metadata_json=json.dumps({"defining_equation": "F = m a"}),
    )
    all_nodes = [{"id": node_id, "title": "Equation Node"}]

    ai_router = _mock_ai_router(fail_enrichment=True)
    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder._enrich_equation_nodes(textbook_id=textbook_id, all_nodes=all_nodes)

    node = await store.get_concept_node(node_id)
    metadata = json.loads(node["metadata_json"])
    assert "equation_components" not in metadata


@pytest.mark.asyncio
async def test_enrich_passes_existing_nodes_to_prompt(store):
    textbook_id, _ = await _seed_textbook_and_chapter(store)
    node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Equation Node",
        node_type="formula",
        level="subsection",
        metadata_json=json.dumps({"defining_equation": "F = m a"}),
    )
    extra_node_id = await store.create_concept_node(
        textbook_id=textbook_id,
        title="Mass",
        node_type="concept",
        level="subsection",
        metadata_json=json.dumps({}),
    )
    all_nodes = [
        {"id": node_id, "title": "Equation Node"},
        {"id": extra_node_id, "title": "Mass"},
    ]

    captured = []

    async def _capture_prompt(prompt):
        if "Existing Knowledge Graph Nodes" in prompt:
            captured.append(prompt)
        return {"equation_components": []}

    ai_router = AsyncMock()
    ai_router.get_json_response = AsyncMock(side_effect=_capture_prompt)
    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder._enrich_equation_nodes(textbook_id=textbook_id, all_nodes=all_nodes)

    assert captured
    assert node_id in captured[0]
    assert extra_node_id in captured[0]
    assert "Equation Node" in captured[0]
    assert "Mass" in captured[0]


@pytest.mark.asyncio
async def test_enrich_called_from_build_graph(store, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(store, chapter_id, "1.1", "Forces", 2, 5)

    sections = [
        {
            "id": section_id,
            "title": "Forces",
            "chapter_id": chapter_id,
            "page_start": 2,
            "page_end": 5,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Forces and motion."},
            ],
        }
    ]

    key_result_response = {
        "concept_groups": [
            {
                "name": "Forces",
                "description": "Force relations",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Newton's Second Law",
                        "node_type": "formula",
                        "defining_equation": "F = m a",
                        "description": "Relation between force, mass, acceleration",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }

    ai_router = _mock_ai_router(
        key_result_response=key_result_response,
        enrichment_response={"equation_components": []},
    )
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    prompts = [call.args[0] for call in ai_router.get_json_response.call_args_list]
    assert any("Existing Knowledge Graph Nodes" in prompt for prompt in prompts)


@pytest.mark.asyncio
async def test_build_graph_completes_even_if_enrichment_fails(
    store, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    textbook_id, chapter_id = await _seed_textbook_and_chapter(store)
    job_id = await store.create_graph_job(textbook_id=textbook_id)
    section_id = await _create_section(store, chapter_id, "1.1", "Forces", 2, 5)

    sections = [
        {
            "id": section_id,
            "title": "Forces",
            "chapter_id": chapter_id,
            "page_start": 2,
            "page_end": 5,
            "section_number": "1.1",
            "section_path": "CH1/1.1",
            "content_entries": [
                {"content_type": "text", "content": "Forces and motion."},
            ],
        }
    ]

    key_result_response = {
        "concept_groups": [
            {
                "name": "Forces",
                "description": "Force relations",
                "node_type": "concept",
                "members": [
                    {
                        "title": "Newton's Second Law",
                        "node_type": "formula",
                        "defining_equation": "F = m a",
                        "description": "Relation between force, mass, acceleration",
                    }
                ],
                "intra_relationships": [],
            }
        ],
        "derivations": [],
    }

    ai_router = _mock_ai_router(
        key_result_response=key_result_response,
        enrichment_response={"equation_components": []},
        fail_enrichment=True,
    )
    monkeypatch.setattr(
        "app.services.knowledge_graph_builder.get_sections_with_content",
        AsyncMock(return_value=sections),
    )

    builder = KnowledgeGraphBuilder(store, ai_router=ai_router)
    await builder.build_graph(textbook_id=textbook_id, job_id=job_id)

    job = await store.get_graph_job(job_id)
    assert job["status"] == "completed"
