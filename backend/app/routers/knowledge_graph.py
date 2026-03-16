from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.config import settings, get_deepseek_api_key
from app.models.knowledge_graph_models import (
    BuildGraphResponse,
    ConceptEdge,
    ConceptNode,
    ConceptNodeDetail,
    GraphData,
    GraphStatusResponse,
)
from app.services.storage import MetadataStore


def get_storage() -> MetadataStore:
    return MetadataStore(db_path=settings.DATA_DIR / "lazy_learn.db")


router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


def _map_node(row: dict) -> dict:
    return {
        "id": row["id"],
        "textbook_id": row["textbook_id"],
        "title": row["title"],
        "description": row.get("description"),
        "node_type": row["node_type"],
        "level": row["level"],
        "source_chapter_id": row.get("source_chapter_id"),
        "source_section_id": row.get("source_section_id"),
        "source_page": row.get("source_page"),
        "metadata": None,
        "created_at": row["created_at"],
    }


def _map_edge(row: dict) -> dict:
    return {
        "id": row["id"],
        "textbook_id": row["textbook_id"],
        "source_node_id": row["source_node_id"],
        "target_node_id": row["target_node_id"],
        "relationship_type": row["relationship_type"],
        "confidence": row.get("confidence", 1.0),
        "reasoning": row.get("reasoning"),
        "created_at": row["created_at"],
    }


@router.post("/{textbook_id}/build", response_model=BuildGraphResponse, status_code=202)
async def build_graph(textbook_id: str, background_tasks: BackgroundTasks):
    store = get_storage()
    await store.initialize()

    textbook = await store.get_textbook(textbook_id)
    if not textbook:
        raise HTTPException(status_code=404, detail="Textbook not found")

    ALLOWED_STATUSES = {"partially_extracted", "extracting", "fully_extracted"}
    if textbook.get("pipeline_status") not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Textbook must have at least some extracted chapters before building a knowledge graph",
        )

    chapters = await store.list_chapters(textbook_id)
    await store.delete_concept_nodes(textbook_id)
    await store.delete_concept_edges(textbook_id)

    job_id = await store.create_graph_job(textbook_id, total_chapters=len(chapters))
    background_tasks.add_task(_build_graph_background, textbook_id, job_id)

    return BuildGraphResponse(
        job_id=job_id,
        textbook_id=textbook_id,
        status="pending",
        message="Graph build started",
    )


@router.get("/{textbook_id}/status", response_model=GraphStatusResponse)
async def get_graph_status(textbook_id: str):
    store = get_storage()
    await store.initialize()

    job = await store.get_latest_graph_job(textbook_id)
    if not job:
        raise HTTPException(
            status_code=404, detail="No graph job found for this textbook"
        )

    return GraphStatusResponse(
        job_id=job["id"],
        textbook_id=job["textbook_id"],
        status=job["status"],
        progress_pct=job.get("progress_pct", 0.0),
        total_chapters=job.get("total_chapters", 0),
        processed_chapters=job.get("processed_chapters", 0),
        error=job.get("error"),
    )


@router.get("/{textbook_id}/graph", response_model=GraphData)
async def get_graph_data(textbook_id: str):
    store = get_storage()
    await store.initialize()

    node_rows = await store.get_concept_nodes(textbook_id)
    if not node_rows:
        raise HTTPException(
            status_code=404, detail="Graph not generated for this textbook"
        )

    edge_rows = await store.get_concept_edges(textbook_id)

    nodes = [ConceptNode(**_map_node(row)) for row in node_rows]
    edges = [ConceptEdge(**_map_edge(row)) for row in edge_rows]

    return GraphData(textbook_id=textbook_id, nodes=nodes, edges=edges)


@router.get("/{textbook_id}/node/{node_id}", response_model=ConceptNodeDetail)
async def get_node_detail(textbook_id: str, node_id: str):
    store = get_storage()
    await store.initialize()

    node_row = await store.get_concept_node(node_id)
    if not node_row:
        raise HTTPException(status_code=404, detail="Node not found")

    all_edges = await store.get_concept_edges(textbook_id)

    outgoing = [
        ConceptEdge(**_map_edge(e)) for e in all_edges if e["source_node_id"] == node_id
    ]
    incoming = [
        ConceptEdge(**_map_edge(e)) for e in all_edges if e["target_node_id"] == node_id
    ]

    return ConceptNodeDetail(
        node=ConceptNode(**_map_node(node_row)),
        incoming_edges=incoming,
        outgoing_edges=outgoing,
    )


@router.delete("/{textbook_id}", status_code=204)
async def delete_graph(textbook_id: str):
    store = get_storage()
    await store.initialize()

    await store.delete_concept_nodes(textbook_id)
    await store.delete_concept_edges(textbook_id)


async def _build_graph_background(textbook_id: str, job_id: str):
    try:
        from app.services.knowledge_graph_builder import KnowledgeGraphBuilder
        from app.services.ai_router import AIRouter

        store = get_storage()
        await store.initialize()
        api_key = await get_deepseek_api_key()
        ai_router = AIRouter(
            deepseek_api_key=api_key, openai_api_key=settings.OPENAI_API_KEY
        )
        builder = KnowledgeGraphBuilder(store=store, ai_router=ai_router)
        await builder.build_graph(textbook_id=textbook_id, job_id=job_id)
    except Exception as e:
        store = get_storage()
        await store.initialize()
        await store.update_graph_job(job_id=job_id, status="failed", error=str(e))
