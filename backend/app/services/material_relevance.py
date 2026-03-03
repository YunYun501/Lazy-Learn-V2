"""Material Relevance Checker — scores textbook TOC entries (chapters/sections/subsections)
against a single university material's topics and persists results in the DB.

Triggered on-demand via the "Check Relevance" button in the UI.
One AI call per textbook keeps latency manageable.
"""
import json
import uuid
from datetime import datetime
from typing import Any

from app.services.storage import MetadataStore

# --------------------------------------------------------------------------- #
# Module-level system prompt (constant string → enables DeepSeek cache hits)   #
# --------------------------------------------------------------------------- #
RELEVANCE_CHECK_SYSTEM_PROMPT = (
    "You are an academic relevance evaluator. "
    "Given a list of university course material topics and a hierarchical textbook "
    "table of contents (chapters, sections, subsections), score each TOC entry's "
    "relevance to the material topics on a 0.0–1.0 scale.\n\n"
    "Rules:\n"
    "1. Score EVERY entry listed — do not skip any.\n"
    "2. 1.0 = perfect topical match, 0.0 = completely unrelated.\n"
    "3. matched_topics must reference specific material topic titles that overlap.\n"
    "4. Keep reasoning to one concise sentence per entry.\n\n"
    "Return ONLY valid JSON:\n"
    '{"results": [\n'
    '  {"entry_id": "...", "relevance_score": 0.0, '
    '"matched_topics": ["topic1"], "reasoning": "..."}\n'
    "]}"
)


class MaterialRelevanceChecker:
    """Score all textbook TOC entries against a single material's topics."""

    def __init__(self, store: MetadataStore, ai_router: Any) -> None:
        self.store = store
        self.ai_router = ai_router

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    async def check(self, material_id: str, course_id: str) -> None:
        """Run full relevance check for *material_id* against every textbook in the course.

        Steps:
        1. Load material summary topics.
        2. For each course textbook → gather chapters/sections/subsections.
        3. Call DeepSeek once per textbook to score entries.
        4. Persist results via ``store.save_relevance_results``.
        5. Update ``relevance_status`` to 'completed' (or 'error' on failure).
        """
        try:
            await self.store.update_material_relevance_status(material_id, "checking")

            # 1. Material topics
            topics = await self._get_material_topics(material_id)
            if not topics:
                # Nothing to match — mark done with no results
                await self.store.save_relevance_results(material_id, [])
                await self.store.update_material_relevance_status(material_id, "completed")
                return

            # 2. Textbooks
            textbooks = await self.store.get_course_textbooks(course_id)
            if not textbooks:
                await self.store.save_relevance_results(material_id, [])
                await self.store.update_material_relevance_status(material_id, "completed")
                return

            all_results: list[dict] = []

            for tb in textbooks:
                tb_id = tb["id"]
                # Build hierarchical TOC lookup
                entries = await self._build_toc_entries(tb_id)
                if not entries:
                    continue

                # 3. AI scoring
                scored = await self._score_entries(topics, entries)

                # 4. Build result rows
                now = datetime.utcnow().isoformat()
                for entry in entries:
                    eid = entry["id"]
                    ai_hit = scored.get(eid, {})
                    raw_score = float(ai_hit.get("relevance_score", 0.0))
                    clamped = max(0.0, min(1.0, raw_score))
                    matched = ai_hit.get("matched_topics", [])
                    reasoning = ai_hit.get("reasoning", "")

                    all_results.append({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "course_id": course_id,
                        "textbook_id": tb_id,
                        "entry_id": eid,
                        "entry_type": entry["type"],
                        "entry_title": entry["title"],
                        "entry_level": entry["level"],
                        "page_start": entry.get("page_start"),
                        "page_end": entry.get("page_end"),
                        "relevance_score": clamped,
                        "matched_topics": json.dumps(matched) if matched else None,
                        "reasoning": reasoning or None,
                        "parent_entry_id": entry.get("parent_id"),
                        "created_at": now,
                    })

            await self.store.save_relevance_results(material_id, all_results)
            await self.store.update_material_relevance_status(material_id, "completed")

        except Exception:
            await self.store.update_material_relevance_status(material_id, "error")
            raise

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _get_material_topics(self, material_id: str) -> list[str]:
        """Extract topic title+description strings from stored material summary."""
        summary = await self.store.get_material_summary(material_id)
        if not summary:
            return []

        raw_json = summary.get("summary_json")
        if not raw_json:
            return []

        try:
            data: dict = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
            topics: list[str] = []
            for topic in data.get("topics", []):
                title: str = topic.get("title", "")
                desc: str = topic.get("description", "")
                topics.append(f"{title}: {desc}" if desc else title)
            return topics
        except (json.JSONDecodeError, AttributeError, TypeError):
            return []

    async def _build_toc_entries(self, textbook_id: str) -> list[dict]:
        """Build a flat list of TOC entries (chapters → sections → subsections) for a textbook.

        Each entry dict has: id, type, title, level, page_start, page_end, parent_id.
        """
        entries: list[dict] = []
        chapters = await self.store.list_chapters(textbook_id)

        for ch in chapters:
            ch_id = ch["id"]
            entries.append({
                "id": ch_id,
                "type": "chapter",
                "title": f"Chapter {ch['chapter_number']}: {ch['title']}",
                "level": 1,
                "page_start": ch.get("page_start"),
                "page_end": ch.get("page_end"),
                "parent_id": None,
            })

            # Level 2 sections
            sections = await self.store.get_sections_for_chapter(ch_id)
            for sec in sections:
                sec_id = sec["id"]
                entries.append({
                    "id": sec_id,
                    "type": "section",
                    "title": sec.get("title") or f"Section {sec.get('section_number', '?')}",
                    "level": 2,
                    "page_start": sec.get("page_start"),
                    "page_end": sec.get("page_end"),
                    "parent_id": ch_id,
                })

                # Level 3 subsections
                subsections = await self.store.get_subsections_for_section(sec_id)
                for sub in subsections:
                    entries.append({
                        "id": sub["id"],
                        "type": "subsection",
                        "title": sub.get("title") or f"Subsection {sub.get('section_number', '?')}",
                        "level": 3,
                        "page_start": sub.get("page_start"),
                        "page_end": sub.get("page_end"),
                        "parent_id": sec_id,
                    })

        return entries

    async def _score_entries(
        self, topics: list[str], entries: list[dict]
    ) -> dict[str, dict]:
        """Call DeepSeek to score each TOC entry. Returns {entry_id: {relevance_score, matched_topics, reasoning}}."""
        topics_text = "\n".join(f"- {t}" for t in topics)
        entries_text = "\n".join(
            f"- [{e['type'].upper()} L{e['level']}] {e['title']} (id: {e['id']}, pages: {e.get('page_start', '?')}-{e.get('page_end', '?')})"
            for e in entries
        )

        messages = [
            {"role": "system", "content": RELEVANCE_CHECK_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Course material topics:\n"
                    f"{topics_text}\n\n"
                    "Textbook table of contents:\n"
                    f"{entries_text}\n\n"
                    "Score each entry's relevance to these material topics."
                ),
            },
        ]

        try:
            response: dict = await self.ai_router.get_json_response(messages)
            results_list = response.get("results", [])
            return {item["entry_id"]: item for item in results_list if "entry_id" in item}
        except Exception:
            # AI failure → return empty scores (all entries get 0.0)
            return {}
