import asyncio
import json
import logging
import time
import uuid
from datetime import datetime

from app.models.knowledge_graph_models import NodeType
from app.services.knowledge_graph_prompts import (
    CROSS_SECTION_RELATIONSHIP_PROMPT,
    EQUATION_ENRICHMENT_PROMPT,
    KEY_RESULT_EXTRACTION_PROMPT,
    parse_enrichment_response,
    parse_key_result_response,
    parse_relationship_response,
)
from app.services.section_content_mapper import get_sections_with_content
from app.services.storage import MetadataStore

logger = logging.getLogger(__name__)

_VALID_NODE_TYPES = {e.value for e in NodeType}


def _safe_node_type(raw: str) -> str:
    """Clamp an LLM-provided node_type to a known enum value, defaulting to 'concept'."""
    val = raw.strip().lower() if raw else "concept"
    return val if val in _VALID_NODE_TYPES else "concept"


class KnowledgeGraphBuilder:
    def __init__(self, store: MetadataStore, ai_router=None):
        self.store = store
        self.ai_router = ai_router

    async def build_graph(self, textbook_id: str, job_id: str) -> None:
        t0 = time.perf_counter()
        try:
            await self.store.update_graph_job(job_id=job_id, status="processing")
            all_chapters = await self.store.list_chapters(textbook_id)
            chapters = [
                ch for ch in all_chapters if ch.get("extraction_status") == "extracted"
            ]
            logger.info(
                "Graph build started",
                extra={
                    "textbook_id": textbook_id,
                    "job_id": job_id,
                    "chapter_count": len(chapters),
                },
            )
            if not chapters:
                await self.store.update_graph_job(
                    job_id=job_id, status="failed", error="No extracted chapters found"
                )
                return

            now = datetime.utcnow().isoformat()
            all_nodes: list[dict] = []
            chapter_node_rows: list[dict] = []

            for chapter in chapters:
                node_id = str(uuid.uuid4())
                chapter_node_rows.append(
                    {
                        "id": node_id,
                        "textbook_id": textbook_id,
                        "title": chapter["title"],
                        "node_type": "concept",
                        "level": "chapter",
                        "description": None,
                        "source_chapter_id": chapter["id"],
                        "source_section_id": None,
                        "source_page": chapter.get("page_start"),
                        "metadata_json": None,
                        "created_at": now,
                    }
                )
                all_nodes.append({"id": node_id, "title": chapter["title"]})

            await self.store.batch_create_concept_nodes(chapter_node_rows)
            await self.store.update_graph_job(job_id=job_id, progress_pct=0.3)

            section_results = await asyncio.gather(
                *[get_sections_with_content(self.store, ch["id"]) for ch in chapters]
            )
            sections_by_chapter: list[dict] = []
            total_sections = 0
            for chapter, sections in zip(chapters, section_results):
                sections_by_chapter.append({"chapter": chapter, "sections": sections})
                total_sections += len(sections)

            concurrency_limit = 30
            semaphore = asyncio.Semaphore(concurrency_limit)
            processed_sections = 0
            concept_lock = asyncio.Lock()
            pending_concepts: dict[str, str] = {}
            collected_nodes: list[dict] = []
            collected_edges: list[dict] = []
            collect_lock = asyncio.Lock()
            edge_count = 0
            last_progress_time = time.perf_counter()
            logger.debug(
                "LLM concurrency configured",
                extra={"concurrency": concurrency_limit},
            )

            async def process_section(chapter: dict, section: dict) -> None:
                nonlocal processed_sections, edge_count, last_progress_time
                async with semaphore:
                    ts = datetime.utcnow().isoformat()
                    section_title = section.get("title", "Unknown Section")
                    section_node_id = str(uuid.uuid4())

                    local_nodes: list[dict] = [
                        {
                            "id": section_node_id,
                            "textbook_id": textbook_id,
                            "title": section_title,
                            "node_type": "concept",
                            "level": "section",
                            "description": None,
                            "source_chapter_id": chapter["id"],
                            "source_section_id": section["id"],
                            "source_page": section.get("page_start"),
                            "metadata_json": None,
                            "created_at": ts,
                        }
                    ]
                    local_edges: list[dict] = []
                    local_all_nodes = [{"id": section_node_id, "title": section_title}]

                    if self.ai_router and hasattr(self.ai_router, "get_json_response"):
                        content_entries = section.get("content_entries", [])
                        text_entries = [
                            e.get("content", "")
                            for e in content_entries
                            if e.get("content_type") == "text"
                        ]
                        equation_entries = [
                            e.get("content", "")
                            for e in content_entries
                            if e.get("content_type") == "equation"
                        ]

                        prompt = KEY_RESULT_EXTRACTION_PROMPT.format(
                            section_title=section_title,
                            section_path=section.get("section_path", ""),
                            parent_concept=chapter.get("title", ""),
                            section_text="\n".join(text_entries),
                            equations_text="\n".join(equation_entries),
                        )

                        raw = None
                        try:
                            logger.info(
                                "Key results extraction started",
                                extra={
                                    "textbook_id": textbook_id,
                                    "chapter_title": chapter.get("title"),
                                },
                            )
                            llm_start = time.perf_counter()
                            raw = await self.ai_router.get_json_response(prompt)
                            parsed = parse_key_result_response(raw)
                            llm_duration_ms = int(
                                (time.perf_counter() - llm_start) * 1000
                            )
                            logger.debug(
                                "LLM call completed",
                                extra={
                                    "duration_ms": llm_duration_ms,
                                    "chapter_title": chapter.get("title"),
                                },
                            )
                        except Exception:
                            raw_snippet = str(raw)[:200] if raw is not None else ""
                            logger.warning(
                                "Unparseable JSON from LLM",
                                extra={
                                    "textbook_id": textbook_id,
                                    "chapter_title": chapter.get("title"),
                                    "response_snippet": raw_snippet,
                                },
                            )
                            parsed = {"concept_groups": [], "derivations": []}

                        node_count = sum(
                            len(group.get("members", [])) + 1
                            for group in parsed.get("concept_groups", [])
                            if isinstance(group, dict)
                        )
                        logger.info(
                            "Key results extraction completed",
                            extra={
                                "textbook_id": textbook_id,
                                "chapter_title": chapter.get("title"),
                                "node_count": node_count,
                            },
                        )

                        concept_ids: dict[str, str] = {}
                        valid_types = {
                            "variant_of",
                            "derives_from",
                            "equivalent_form",
                            "generalizes",
                            "specializes",
                            "uses",
                            "prerequisite_of",
                        }

                        for group in parsed.get("concept_groups", []):
                            group_title = group.get("name", "Unknown")
                            async with concept_lock:
                                if group_title in pending_concepts:
                                    group_node_id = pending_concepts[group_title]
                                else:
                                    group_node_id = str(uuid.uuid4())
                                    pending_concepts[group_title] = group_node_id
                                    local_nodes.append(
                                        {
                                            "id": group_node_id,
                                            "textbook_id": textbook_id,
                                            "title": group_title,
                                            "node_type": _safe_node_type(
                                                group.get("node_type", "concept")
                                            ),
                                            "level": "subsection",
                                            "description": group.get("description"),
                                            "source_chapter_id": chapter["id"],
                                            "source_section_id": section["id"],
                                            "metadata_json": json.dumps({}),
                                            "created_at": ts,
                                        }
                                    )
                                    local_all_nodes.append(
                                        {"id": group_node_id, "title": group_title}
                                    )
                            concept_ids[group_title] = group_node_id

                            for member in group.get("members", []):
                                member_title = member.get("title", "Unknown")
                                member_node_id = ""
                                async with concept_lock:
                                    if member_title in pending_concepts:
                                        member_node_id = pending_concepts[member_title]
                                    else:
                                        member_node_id = str(uuid.uuid4())
                                        pending_concepts[member_title] = member_node_id
                                        local_nodes.append(
                                            {
                                                "id": member_node_id,
                                                "textbook_id": textbook_id,
                                                "title": member_title,
                                                "node_type": _safe_node_type(
                                                    member.get("node_type", "concept")
                                                ),
                                                "level": "subsection",
                                                "description": member.get(
                                                    "description"
                                                ),
                                                "source_chapter_id": chapter["id"],
                                                "source_section_id": section["id"],
                                                "metadata_json": json.dumps(
                                                    {
                                                        "defining_equation": member.get(
                                                            "defining_equation",
                                                            "",
                                                        ),
                                                    }
                                                ),
                                                "created_at": ts,
                                            }
                                        )
                                        local_all_nodes.append(
                                            {
                                                "id": member_node_id,
                                                "title": member_title,
                                            }
                                        )
                                if not member_node_id:
                                    continue
                                concept_ids[member_title] = member_node_id
                                local_edges.append(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "textbook_id": textbook_id,
                                        "source_node_id": group_node_id,
                                        "target_node_id": member_node_id,
                                        "relationship_type": "contains",
                                        "confidence": 1.0,
                                        "reasoning": None,
                                        "metadata_json": None,
                                        "created_at": ts,
                                    }
                                )

                            for rel in group.get("intra_relationships", []):
                                source_id = concept_ids.get(rel.get("source", ""))
                                target_id = concept_ids.get(rel.get("target", ""))
                                if not source_id or not target_id:
                                    continue
                                rel_type = rel.get("relationship_type", "variant_of")
                                if rel_type not in valid_types:
                                    rel_type = "variant_of"
                                local_edges.append(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "textbook_id": textbook_id,
                                        "source_node_id": source_id,
                                        "target_node_id": target_id,
                                        "relationship_type": rel_type,
                                        "confidence": 1.0,
                                        "reasoning": rel.get("reasoning"),
                                        "metadata_json": None,
                                        "created_at": ts,
                                    }
                                )

                        for deriv in parsed.get("derivations", []):
                            source_id = concept_ids.get(deriv.get("source", ""))
                            target_id = concept_ids.get(deriv.get("target", ""))
                            if not source_id or not target_id:
                                continue
                            local_edges.append(
                                {
                                    "id": str(uuid.uuid4()),
                                    "textbook_id": textbook_id,
                                    "source_node_id": source_id,
                                    "target_node_id": target_id,
                                    "relationship_type": "derives_from",
                                    "confidence": 1.0,
                                    "reasoning": deriv.get("description"),
                                    "metadata_json": json.dumps(
                                        {
                                            "derivation_steps": deriv.get(
                                                "derivation_steps", []
                                            ),
                                            "transformation_context": deriv.get(
                                                "transformation_context", {}
                                            ),
                                        }
                                    ),
                                    "created_at": ts,
                                }
                            )

                    async with collect_lock:
                        collected_nodes.extend(local_nodes)
                        collected_edges.extend(local_edges)
                        all_nodes.extend(local_all_nodes)
                        edge_count += len(local_edges)

                    processed_sections += 1
                    now_time = time.perf_counter()
                    if now_time - last_progress_time >= 1.0:
                        last_progress_time = now_time
                        progress = (
                            0.3 + (processed_sections / max(total_sections, 1)) * 0.5
                        )
                        await self.store.update_graph_job(
                            job_id=job_id, progress_pct=round(progress, 2)
                        )

            tasks = []
            for entry in sections_by_chapter:
                chapter = entry["chapter"]
                for section in entry["sections"]:
                    tasks.append(process_section(chapter, section))

            if tasks:
                await asyncio.gather(*tasks)

            if collected_nodes:
                await self.store.batch_create_concept_nodes(collected_nodes)
            if collected_edges:
                await self.store.batch_create_concept_edges(collected_edges)

            await self.store.update_graph_job(job_id=job_id, progress_pct=0.8)

            if all_nodes and self.ai_router:
                await self._enrich_equation_nodes(
                    textbook_id=textbook_id, all_nodes=all_nodes
                )

            await self.store.update_graph_job(job_id=job_id, progress_pct=0.9)

            rel_edge_count = 0
            if all_nodes and self.ai_router:
                rel_edge_count = await self._extract_relationships(
                    textbook_id=textbook_id, nodes=all_nodes
                )

            duration_s = round(time.perf_counter() - t0, 2)
            logger.info(
                "Graph build completed",
                extra={
                    "textbook_id": textbook_id,
                    "job_id": job_id,
                    "total_nodes": len(all_nodes),
                    "total_edges": edge_count + rel_edge_count,
                    "duration_s": duration_s,
                },
            )
            await self.store.update_graph_job(
                job_id=job_id,
                status="completed",
                progress_pct=1.0,
                completed_at=datetime.utcnow().isoformat(),
            )
        except Exception as exc:
            logger.error(
                "Graph build failed",
                extra={"textbook_id": textbook_id, "job_id": job_id},
                exc_info=True,
            )
            await self.store.update_graph_job(
                job_id=job_id,
                status="failed",
                error=str(exc),
            )
            raise

    async def _enrich_equation_nodes(
        self, textbook_id: str, all_nodes: list[dict]
    ) -> None:
        ai_router = self.ai_router
        if not ai_router or not hasattr(ai_router, "get_json_response"):
            return

        nodes = await self.store.get_concept_nodes(textbook_id)
        if not nodes:
            return

        existing_nodes_list = [
            {"id": node["id"], "title": node["title"]} for node in all_nodes
        ]
        equation_nodes = []
        for node in nodes:
            try:
                metadata = json.loads(node.get("metadata_json") or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            equation_latex = metadata.get("defining_equation", "")
            if equation_latex:
                equation_nodes.append(
                    {"node": node, "metadata": metadata, "equation": equation_latex}
                )

        if not equation_nodes:
            return

        semaphore = asyncio.Semaphore(20)
        collected_metadata_updates: list[tuple[str, str]] = []
        collected_edges: list[dict] = []
        collect_lock = asyncio.Lock()

        async def _enrich(node_entry: dict) -> None:
            async with semaphore:
                try:
                    metadata = node_entry["metadata"].copy()
                    equation_latex = node_entry["equation"]
                    prompt = EQUATION_ENRICHMENT_PROMPT.format(
                        equation_latex=equation_latex,
                        section_text="",
                        existing_nodes_json=json.dumps(existing_nodes_list),
                    )
                    raw = await ai_router.get_json_response(prompt)
                    components = parse_enrichment_response(raw)
                    if components:
                        metadata["equation_components"] = components
                        ts = datetime.utcnow().isoformat()
                        local_edges: list[dict] = []
                        for comp in components:
                            if comp.get("type") == "calculated" and comp.get(
                                "linked_node_id"
                            ):
                                local_edges.append(
                                    {
                                        "id": str(uuid.uuid4()),
                                        "textbook_id": textbook_id,
                                        "source_node_id": node_entry["node"]["id"],
                                        "target_node_id": comp["linked_node_id"],
                                        "relationship_type": "uses",
                                        "confidence": 1.0,
                                        "reasoning": f"{comp.get('symbol', '')} ({comp.get('name', '')})",
                                        "metadata_json": None,
                                        "created_at": ts,
                                    }
                                )
                        async with collect_lock:
                            collected_metadata_updates.append(
                                (node_entry["node"]["id"], json.dumps(metadata))
                            )
                            collected_edges.extend(local_edges)
                except Exception:
                    return

        await asyncio.gather(*[_enrich(node_entry) for node_entry in equation_nodes])

        if collected_metadata_updates:
            await self.store.batch_update_concept_node_metadata(
                collected_metadata_updates
            )
        if collected_edges:
            await self.store.batch_create_concept_edges(collected_edges)

    async def _extract_relationships(self, textbook_id: str, nodes: list[dict]) -> int:
        ai_router = self.ai_router
        if not ai_router or not hasattr(ai_router, "get_json_response"):
            return 0
        if len(nodes) < 2:
            return 0

        logger.info(
            "Cross-section relationship extraction started",
            extra={"textbook_id": textbook_id, "node_count": len(nodes)},
        )

        concepts_str = "\n".join(
            f"{index + 1}. {node['title']}" for index, node in enumerate(nodes[:50])
        )
        prompt = CROSS_SECTION_RELATIONSHIP_PROMPT.format(
            textbook_title=f"Textbook {textbook_id}",
            concepts_list=concepts_str,
        )

        raw = None
        try:
            raw = await ai_router.get_json_response(prompt)
            if isinstance(raw, dict):
                relationships = raw.get("relationships", [])
            elif isinstance(raw, list):
                relationships = raw
            elif isinstance(raw, str):
                relationships = parse_relationship_response(raw)
            else:
                relationships = []
            if not isinstance(relationships, list):
                relationships = []
        except Exception:
            raw_snippet = str(raw)[:200] if raw is not None else ""
            logger.warning(
                "Unparseable JSON from LLM",
                extra={
                    "textbook_id": textbook_id,
                    "response_snippet": raw_snippet,
                },
            )
            return 0

        title_to_id = {node["title"]: node["id"] for node in nodes}
        ts = datetime.utcnow().isoformat()
        collected_edges: list[dict] = []
        for rel in relationships:
            source_id = title_to_id.get(rel.get("source", ""))
            target_id = title_to_id.get(rel.get("target", ""))
            if not source_id or not target_id:
                continue
            try:
                confidence = float(rel.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0

            collected_edges.append(
                {
                    "id": str(uuid.uuid4()),
                    "textbook_id": textbook_id,
                    "source_node_id": source_id,
                    "target_node_id": target_id,
                    "relationship_type": rel.get("relationship_type", "uses"),
                    "confidence": confidence,
                    "reasoning": rel.get("reasoning"),
                    "metadata_json": None,
                    "created_at": ts,
                }
            )

        if collected_edges:
            await self.store.batch_create_concept_edges(collected_edges)

        logger.info(
            "Cross-section relationship extraction completed",
            extra={"textbook_id": textbook_id, "edge_count": len(collected_edges)},
        )
        return len(collected_edges)
