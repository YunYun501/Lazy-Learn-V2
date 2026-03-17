import asyncio
import json
from datetime import datetime

from app.models.knowledge_graph_models import NodeType
from app.services.knowledge_graph_prompts import (
    CROSS_SECTION_RELATIONSHIP_PROMPT,
    KEY_RESULT_EXTRACTION_PROMPT,
    parse_key_result_response,
    parse_relationship_response,
)
from app.services.section_content_mapper import get_sections_with_content
from app.services.storage import MetadataStore

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
        try:
            await self.store.update_graph_job(job_id=job_id, status="processing")
            all_chapters = await self.store.list_chapters(textbook_id)
            chapters = [
                ch for ch in all_chapters if ch.get("extraction_status") == "extracted"
            ]
            if not chapters:
                await self.store.update_graph_job(
                    job_id=job_id, status="failed", error="No extracted chapters found"
                )
                return
            all_nodes: list[dict] = []
            for chapter in chapters:
                node_id = await self.store.create_concept_node(
                    textbook_id=textbook_id,
                    title=chapter["title"],
                    node_type="concept",
                    level="chapter",
                    source_chapter_id=chapter["id"],
                    source_page=chapter.get("page_start"),
                )
                all_nodes.append({"id": node_id, "title": chapter["title"]})

            await self.store.update_graph_job(job_id=job_id, progress_pct=0.3)

            sections_by_chapter = []
            total_sections = 0
            for chapter in chapters:
                sections = await get_sections_with_content(self.store, chapter["id"])
                sections_by_chapter.append({"chapter": chapter, "sections": sections})
                total_sections += len(sections)

            semaphore = asyncio.Semaphore(3)
            processed_sections = 0
            concept_lock = asyncio.Lock()
            pending_concepts: dict[str, str] = {}

            async def process_section(chapter, section):
                nonlocal processed_sections
                async with semaphore:
                    section_node_id = await self.store.create_concept_node(
                        textbook_id=textbook_id,
                        title=section.get("title", "Unknown Section"),
                        node_type="concept",
                        level="section",
                        source_chapter_id=chapter["id"],
                        source_section_id=section["id"],
                        source_page=section.get("page_start"),
                    )
                    all_nodes.append(
                        {"id": section_node_id, "title": section.get("title", "")}
                    )

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
                            section_title=section.get("title", "Unknown Section"),
                            section_path=section.get("section_path", ""),
                            parent_concept=chapter.get("title", ""),
                            section_text="\n".join(text_entries),
                            equations_text="\n".join(equation_entries),
                        )

                        try:
                            raw = await self.ai_router.get_json_response(prompt)
                            parsed = parse_key_result_response(raw)
                        except Exception:
                            parsed = {"concept_groups": [], "derivations": []}

                        concept_ids = {}
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
                                    existing_id = await self._deduplicate_concept(
                                        textbook_id, group_title
                                    )
                                    if existing_id:
                                        group_node_id = existing_id
                                    else:
                                        group_node_id = (
                                            await self.store.create_concept_node(
                                                textbook_id=textbook_id,
                                                title=group_title,
                                                node_type=_safe_node_type(
                                                    group.get("node_type", "concept")
                                                ),
                                                level="subsection",
                                                description=group.get("description"),
                                                source_chapter_id=chapter["id"],
                                                source_section_id=section["id"],
                                                metadata_json=json.dumps({}),
                                            )
                                        )
                                        all_nodes.append(
                                            {"id": group_node_id, "title": group_title}
                                        )
                                    pending_concepts[group_title] = group_node_id
                            concept_ids[group_title] = group_node_id

                            for member in group.get("members", []):
                                member_title = member.get("title", "Unknown")
                                async with concept_lock:
                                    if member_title in pending_concepts:
                                        member_node_id = pending_concepts[member_title]
                                    else:
                                        existing_id = await self._deduplicate_concept(
                                            textbook_id, member_title
                                        )
                                        if existing_id:
                                            member_node_id = existing_id
                                        else:
                                            member_node_id = await self.store.create_concept_node(
                                                textbook_id=textbook_id,
                                                title=member_title,
                                                node_type=_safe_node_type(
                                                    member.get("node_type", "concept")
                                                ),
                                                level="subsection",
                                                description=member.get("description"),
                                                source_chapter_id=chapter["id"],
                                                source_section_id=section["id"],
                                                metadata_json=json.dumps(
                                                    {
                                                        "defining_equation": member.get(
                                                            "defining_equation", ""
                                                        ),
                                                    }
                                                ),
                                            )
                                            all_nodes.append(
                                                {
                                                    "id": member_node_id,
                                                    "title": member_title,
                                                }
                                            )
                                        pending_concepts[member_title] = member_node_id
                                concept_ids[member_title] = member_node_id

                                await self.store.create_concept_edge(
                                    textbook_id=textbook_id,
                                    source_node_id=group_node_id,
                                    target_node_id=member_node_id,
                                    relationship_type="contains",
                                )

                            for rel in group.get("intra_relationships", []):
                                source_id = concept_ids.get(rel.get("source", ""))
                                target_id = concept_ids.get(rel.get("target", ""))
                                if not source_id or not target_id:
                                    continue
                                rel_type = rel.get("relationship_type", "variant_of")
                                if rel_type not in valid_types:
                                    rel_type = "variant_of"
                                await self.store.create_concept_edge(
                                    textbook_id=textbook_id,
                                    source_node_id=source_id,
                                    target_node_id=target_id,
                                    relationship_type=rel_type,
                                    reasoning=rel.get("reasoning"),
                                )

                        for deriv in parsed.get("derivations", []):
                            source_id = concept_ids.get(deriv.get("source", ""))
                            target_id = concept_ids.get(deriv.get("target", ""))
                            if not source_id or not target_id:
                                continue
                            await self.store.create_concept_edge(
                                textbook_id=textbook_id,
                                source_node_id=source_id,
                                target_node_id=target_id,
                                relationship_type="derives_from",
                                reasoning=deriv.get("description"),
                                metadata_json=json.dumps(
                                    {
                                        "derivation_steps": deriv.get(
                                            "derivation_steps", []
                                        ),
                                    }
                                ),
                            )

                    processed_sections += 1
                    progress = 0.3 + (processed_sections / max(total_sections, 1)) * 0.5
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

            await self.store.update_graph_job(job_id=job_id, progress_pct=0.8)

            if all_nodes and self.ai_router:
                await self._enrich_equation_nodes(
                    textbook_id=textbook_id, all_nodes=all_nodes
                )

            await self.store.update_graph_job(job_id=job_id, progress_pct=0.9)

            if all_nodes and self.ai_router:
                await self._extract_relationships(
                    textbook_id=textbook_id, nodes=all_nodes
                )

            await self.store.update_graph_job(
                job_id=job_id,
                status="completed",
                progress_pct=1.0,
                completed_at=datetime.utcnow().isoformat(),
            )
        except Exception as exc:
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

        semaphore = asyncio.Semaphore(3)

        async def _enrich(node_entry: dict) -> None:
            async with semaphore:
                try:
                    from app.services.knowledge_graph_prompts import (
                        EQUATION_ENRICHMENT_PROMPT,
                        parse_enrichment_response,
                    )

                    metadata = node_entry["metadata"]
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
                        await self.store.update_concept_node_metadata(
                            node_entry["node"]["id"], json.dumps(metadata)
                        )
                except Exception:
                    return

        await asyncio.gather(*[_enrich(node_entry) for node_entry in equation_nodes])

    async def _extract_relationships(self, textbook_id: str, nodes: list[dict]) -> None:
        ai_router = self.ai_router
        if not ai_router or not hasattr(ai_router, "get_json_response"):
            return
        if len(nodes) < 2:
            return

        concepts_str = "\n".join(
            f"{index + 1}. {node['title']}" for index, node in enumerate(nodes[:50])
        )
        prompt = CROSS_SECTION_RELATIONSHIP_PROMPT.format(
            textbook_title=f"Textbook {textbook_id}",
            concepts_list=concepts_str,
        )

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
            return

        title_to_id = {node["title"]: node["id"] for node in nodes}
        for rel in relationships:
            source_id = title_to_id.get(rel.get("source", ""))
            target_id = title_to_id.get(rel.get("target", ""))
            if not source_id or not target_id:
                continue
            try:
                confidence = float(rel.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0

            await self.store.create_concept_edge(
                textbook_id=textbook_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relationship_type=rel.get("relationship_type", "uses"),
                confidence=confidence,
                reasoning=rel.get("reasoning"),
            )

    async def _deduplicate_concept(self, textbook_id: str, title: str) -> str | None:
        import aiosqlite

        async with aiosqlite.connect(self.store.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id FROM concept_nodes WHERE textbook_id = ? AND title = ? LIMIT 1",
                (textbook_id, title),
            ) as cursor:
                row = await cursor.fetchone()
        if row:
            return dict(row)["id"]
        return None
