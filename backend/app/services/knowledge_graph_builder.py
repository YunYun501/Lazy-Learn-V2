import json
from datetime import datetime

from app.services.knowledge_graph_prompts import (
    CONCEPT_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
    SECTION_CONCEPT_PROMPT,
    parse_concept_extraction_response,
    parse_relationship_response,
    parse_section_concept_response,
)
from app.services.latex_parser import (
    EquationInfo,
    build_variable_cooccurrence,
    parse_equation,
)
from app.services.section_content_mapper import get_sections_with_content
from app.services.storage import MetadataStore


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
            section_nodes: dict[str, str] = {}
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

            for index, chapter in enumerate(chapters):
                desc = await self._load_chapter_description(
                    textbook_id,
                    chapter["chapter_number"],
                    chapter_id=chapter["id"],
                    chapter_title=chapter.get("title", ""),
                )
                if desc:
                    section_nodes_from_desc = (
                        await self._extract_concepts_from_description(
                            textbook_id=textbook_id,
                            chapter_id=chapter["id"],
                            chapter_desc=desc,
                        )
                    )
                    all_nodes.extend(section_nodes_from_desc)

                await self.store.update_graph_job(
                    job_id=job_id,
                    processed_chapters=index + 1,
                )

            sections_by_chapter: list[dict] = []
            total_sections = 0
            for chapter in chapters:
                sections = await get_sections_with_content(self.store, chapter["id"])
                sections_by_chapter.append({"chapter": chapter, "sections": sections})
                total_sections += len(sections)

            if total_sections == 0:
                await self.store.update_graph_job(job_id=job_id, progress_pct=0.7)
            else:
                processed_sections = 0
                for entry in sections_by_chapter:
                    chapter = entry["chapter"]
                    for section in entry["sections"]:
                        section_node_id = await self.store.create_concept_node(
                            textbook_id=textbook_id,
                            title=section.get("title", "Unknown Section"),
                            node_type="concept",
                            level="section",
                            source_chapter_id=chapter["id"],
                            source_section_id=section["id"],
                            source_page=section.get("page_start"),
                        )
                        section_nodes[section["id"]] = section_node_id
                        all_nodes.append(
                            {"id": section_node_id, "title": section.get("title", "")}
                        )

                        if self.ai_router and hasattr(
                            self.ai_router, "get_json_response"
                        ):
                            content_entries = section.get("content_entries", [])
                            text_entries = [
                                entry.get("content", "")
                                for entry in content_entries
                                if entry.get("content_type") == "text"
                            ]
                            equation_entries = [
                                entry.get("content", "")
                                for entry in content_entries
                                if entry.get("content_type") == "equation"
                            ]

                            prompt = SECTION_CONCEPT_PROMPT.format(
                                section_title=section.get("title", "Unknown Section"),
                                section_path=section.get("section_path", ""),
                                parent_concept=chapter.get("title", ""),
                                section_text="\n".join(text_entries),
                                equations_text="\n".join(equation_entries),
                            )

                            try:
                                raw = await self.ai_router.get_json_response(prompt)
                                parsed = parse_section_concept_response(raw)
                            except Exception:
                                parsed = {"concepts": [], "section_relationships": []}

                            concept_ids: dict[str, str] = {}
                            for concept in parsed.get("concepts", []):
                                title = concept.get("title", "Unknown")
                                existing_id = await self._deduplicate_concept(
                                    textbook_id=textbook_id,
                                    title=title,
                                )
                                if existing_id:
                                    node_id = existing_id
                                else:
                                    node_id = await self.store.create_concept_node(
                                        textbook_id=textbook_id,
                                        title=title,
                                        node_type=concept.get("node_type", "concept"),
                                        level="subsection",
                                        description=concept.get("description"),
                                        source_chapter_id=chapter["id"],
                                        source_section_id=section["id"],
                                        metadata_json=json.dumps(
                                            {
                                                "aliases": concept.get("aliases", []),
                                                "prerequisites": concept.get(
                                                    "prerequisites", []
                                                ),
                                            }
                                        ),
                                    )
                                    all_nodes.append({"id": node_id, "title": title})

                                concept_ids[title] = node_id

                            for rel in parsed.get("section_relationships", []):
                                source_id = concept_ids.get(rel.get("source", ""))
                                target_id = concept_ids.get(rel.get("target", ""))
                                if not source_id or not target_id:
                                    continue
                                await self.store.create_concept_edge(
                                    textbook_id=textbook_id,
                                    source_node_id=source_id,
                                    target_node_id=target_id,
                                    relationship_type=rel.get(
                                        "relationship_type", "uses"
                                    ),
                                    reasoning=rel.get("reasoning"),
                                )

                        processed_sections += 1
                        progress = (
                            0.3 + (processed_sections / max(total_sections, 1)) * 0.4
                        )
                        await self.store.update_graph_job(
                            job_id=job_id,
                            progress_pct=round(progress, 2),
                        )

                await self.store.update_graph_job(job_id=job_id, progress_pct=0.7)

            if total_sections == 0:
                await self.store.update_graph_job(job_id=job_id, progress_pct=0.9)
            else:
                processed_sections = 0
                for entry in sections_by_chapter:
                    chapter = entry["chapter"]
                    for section in entry["sections"]:
                        section_node_id = section_nodes.get(section["id"])
                        if not section_node_id:
                            processed_sections += 1
                            continue

                        content_entries = section.get("content_entries", [])
                        equations = [
                            entry
                            for entry in content_entries
                            if entry.get("content_type") == "equation"
                        ]

                        parsed_equations: list[tuple[str, EquationInfo]] = []
                        equation_lookup: dict[str, EquationInfo] = {}
                        for entry in equations:
                            raw_equation = entry.get("content", "")
                            info = parse_equation(raw_equation)
                            if not info.is_parseable:
                                continue
                            equation_node_id = await self.store.create_concept_node(
                                textbook_id=textbook_id,
                                title="Equation",
                                node_type="equation",
                                level="equation",
                                source_chapter_id=chapter["id"],
                                source_section_id=section["id"],
                                source_page=entry.get("page_number"),
                                metadata_json=json.dumps(
                                    {
                                        "variables": sorted(list(info.variables)),
                                        "raw_latex": info.raw_latex,
                                    }
                                ),
                            )
                            all_nodes.append(
                                {"id": equation_node_id, "title": "Equation"}
                            )
                            await self.store.create_concept_edge(
                                textbook_id=textbook_id,
                                source_node_id=section_node_id,
                                target_node_id=equation_node_id,
                                relationship_type="contains",
                            )
                            parsed_equations.append((equation_node_id, info))
                            equation_lookup[equation_node_id] = info

                        if parsed_equations:
                            cooccurrences = build_variable_cooccurrence(
                                parsed_equations
                            )
                            for eq_a, eq_b, shared_count in cooccurrences:
                                info_a = equation_lookup.get(eq_a)
                                info_b = equation_lookup.get(eq_b)
                                if not info_a or not info_b:
                                    continue
                                shared_vars = sorted(
                                    info_a.variables.intersection(info_b.variables)
                                )
                                max_vars = max(
                                    len(info_a.variables), len(info_b.variables), 1
                                )
                                confidence = shared_count / max_vars
                                await self.store.create_concept_edge(
                                    textbook_id=textbook_id,
                                    source_node_id=eq_a,
                                    target_node_id=eq_b,
                                    relationship_type="shared_variables",
                                    confidence=confidence,
                                    reasoning=f"Shared variables: {shared_vars}",
                                )

                        processed_sections += 1
                        progress = (
                            0.7 + (processed_sections / max(total_sections, 1)) * 0.2
                        )
                        await self.store.update_graph_job(
                            job_id=job_id,
                            progress_pct=round(progress, 2),
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

    async def _load_chapter_description(
        self,
        textbook_id: str,
        chapter_number: str,
        chapter_id: str = "",
        chapter_title: str = "",
    ):
        import aiosqlite

        async with aiosqlite.connect(self.store.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT content_type, content FROM extracted_content WHERE chapter_id = ? ORDER BY rowid",
                (chapter_id,),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return None

        text_parts = []
        has_math = False
        for row in rows:
            r = dict(row)
            content = r.get("content") or ""
            if r["content_type"] == "text":
                text_parts.append(content[:500])
            elif r["content_type"] == "equation":
                has_math = True
                text_parts.append(content[:200])

        combined = "\n".join(text_parts)[:3000]

        return {
            "chapter_title": chapter_title or f"Chapter {chapter_number}",
            "chapter_number": chapter_number,
            "raw": combined,
            "key_concepts": [],
            "prerequisites": [],
            "mathematical_content": has_math,
        }

    async def _extract_concepts_from_description(
        self, textbook_id: str, chapter_id: str, chapter_desc: dict
    ) -> list[dict]:
        if not self.ai_router or not hasattr(self.ai_router, "get_json_response"):
            return []

        key_concepts_str = (
            ", ".join(
                c.get("name", "") for c in chapter_desc.get("key_concepts", [])
            ).strip()
            or "None"
        )
        prerequisites_str = ", ".join(chapter_desc.get("prerequisites", [])).strip()
        if not prerequisites_str:
            prerequisites_str = "None"

        prompt = CONCEPT_EXTRACTION_PROMPT.format(
            chapter_title=chapter_desc.get("chapter_title", "Unknown"),
            chapter_number=chapter_desc.get("chapter_number", "?"),
            key_concepts=key_concepts_str,
            prerequisites=prerequisites_str,
            mathematical_content=chapter_desc.get("mathematical_content", False),
            chapter_content=chapter_desc.get("raw", "No content available")[:2000],
        )

        try:
            raw = await self.ai_router.get_json_response(prompt)
            if isinstance(raw, dict):
                concepts = raw.get("concepts", [])
            elif isinstance(raw, list):
                concepts = raw
            elif isinstance(raw, str):
                concepts = parse_concept_extraction_response(raw)
            else:
                concepts = []
            if not isinstance(concepts, list):
                concepts = []
        except Exception:
            return []

        nodes: list[dict] = []
        for concept in concepts:
            title = concept.get("title", "Unknown")
            node_id = await self.store.create_concept_node(
                textbook_id=textbook_id,
                title=title,
                node_type=concept.get("node_type", "concept"),
                level="section",
                description=concept.get("description"),
                source_chapter_id=chapter_id,
                metadata_json=json.dumps({"aliases": concept.get("aliases", [])}),
            )
            nodes.append({"id": node_id, "title": title})
        return nodes

    async def _extract_relationships(self, textbook_id: str, nodes: list[dict]) -> None:
        if not self.ai_router or not hasattr(self.ai_router, "get_json_response"):
            return
        if len(nodes) < 2:
            return

        concepts_str = "\n".join(
            f"{index + 1}. {node['title']}" for index, node in enumerate(nodes[:50])
        )
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            textbook_title=f"Textbook {textbook_id}",
            concepts_list=concepts_str,
        )

        try:
            raw = await self.ai_router.get_json_response(prompt)
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
