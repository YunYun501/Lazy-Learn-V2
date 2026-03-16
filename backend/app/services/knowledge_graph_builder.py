import json
from datetime import datetime
from pathlib import Path

from app.services.knowledge_graph_prompts import (
    CONCEPT_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
    parse_concept_extraction_response,
    parse_relationship_response,
)
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
            total = len(chapters)

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

            for index, chapter in enumerate(chapters):
                desc = await self._load_chapter_description(
                    textbook_id, chapter["chapter_number"]
                )
                if desc:
                    section_nodes = await self._extract_concepts_from_description(
                        textbook_id=textbook_id,
                        chapter_id=chapter["id"],
                        chapter_desc=desc,
                    )
                    all_nodes.extend(section_nodes)

                await self.store.update_graph_job(
                    job_id=job_id,
                    processed_chapters=index + 1,
                    progress_pct=round((index + 1) / max(total, 1), 2),
                )

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

    async def _load_chapter_description(self, textbook_id: str, chapter_number: str):
        desc_path = (
            Path("data") / "descriptions" / textbook_id / f"chapter_{chapter_number}.md"
        )
        if not desc_path.exists():
            return None
        try:
            content = desc_path.read_text(encoding="utf-8")
            return {
                "chapter_title": f"Chapter {chapter_number}",
                "chapter_number": chapter_number,
                "raw": content,
                "key_concepts": [],
                "prerequisites": [],
                "mathematical_content": False,
            }
        except Exception:
            return None

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
        )

        try:
            raw = await self.ai_router.get_json_response(prompt)
            if isinstance(raw, list):
                concepts = raw
            elif isinstance(raw, str):
                concepts = parse_concept_extraction_response(raw)
            else:
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
            if isinstance(raw, list):
                relationships = raw
            elif isinstance(raw, str):
                relationships = parse_relationship_response(raw)
            else:
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
