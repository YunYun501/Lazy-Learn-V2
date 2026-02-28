"""Relevance Matcher service — scores textbook chapters against course material topics.

Results are computed on-demand (not persisted) during the TOC verification phase.
The caller (orchestrator) uses these scores to pre-select chapters for verification.
"""
import json
from typing import Any

from app.models.pipeline_models import RelevanceResult
from app.services.storage import MetadataStore


class RelevanceMatcher:
    """Score textbook chapters against course material topics using DeepSeek."""

    def __init__(self, store: MetadataStore, ai_router: Any) -> None:
        self.store = store
        self.ai_router = ai_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def match_chapters(
        self, textbook_id: str, course_id: str
    ) -> list[RelevanceResult]:
        """Return chapters scored against course material, sorted by score descending.

        Returns an empty list immediately if the course has no material summaries
        (no DeepSeek call is made in that case).
        """
        # 1. Fetch all material summaries for the course.
        summaries = await self._get_course_summaries(course_id)
        if not summaries:
            return []

        # 2. Fetch all chapters for the textbook.
        chapters = await self.store.list_chapters(textbook_id)
        if not chapters:
            return []

        # 3. Extract topic strings from summaries.
        topics = self._extract_topics(summaries)

        # 4. Build the relevance-scoring prompt.
        prompt = self._build_prompt(topics, chapters)

        # 5. Call DeepSeek via AIRouter and get structured JSON back.
        response: dict = await self.ai_router.get_json_response(prompt)

        # 6. Parse response → RelevanceResult list, clamp scores, sort.
        results = self._parse_response(response)
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_course_summaries(self, course_id: str) -> list[dict]:
        """Fetch stored material summaries for a course via the MetadataStore."""
        materials = await self.store.list_university_materials(course_id)
        summaries: list[dict] = []
        for mat in materials:
            summary = await self.store.get_material_summary(mat["id"])
            if summary:
                summaries.append(summary)
        return summaries

    def _extract_topics(self, summaries: list[dict]) -> list[str]:
        """Parse topic titles + descriptions from raw summary dicts."""
        topics: list[str] = []
        for summary in summaries:
            raw_json = summary.get("summary_json")
            if not raw_json:
                continue
            try:
                data: dict = (
                    json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                )
                for topic in data.get("topics", []):
                    title: str = topic.get("title", "")
                    desc: str = topic.get("description", "")
                    topics.append(f"{title}: {desc}" if desc else title)
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue
        return topics

    def _build_prompt(self, topics: list[str], chapters: list[dict]) -> str:
        """Construct the DeepSeek relevance-scoring prompt."""
        topics_text = "\n".join(f"- {t}" for t in topics)
        chapters_text = "\n".join(
            f"- Chapter {ch['chapter_number']}: {ch['title']} (id: {ch['id']})"
            for ch in chapters
        )
        return (
            "Given these course material topics:\n"
            f"{topics_text}\n\n"
            "And these textbook chapters:\n"
            f"{chapters_text}\n\n"
            "Rate the relevance of each chapter to the course material (0.0 to 1.0 score).\n"
            "For each chapter, identify which material topics it matches.\n"
            "Provide brief reasoning for the score.\n\n"
            'Return JSON: {"results": [{"chapter_id": "...", "chapter_title": "...", '
            '"relevance_score": 0.0-1.0, "matched_topics": ["topic1", "topic2"], '
            '"reasoning": "..."}]}'
        )

    def _parse_response(self, response: dict) -> list[RelevanceResult]:
        """Convert AI response dict to RelevanceResult list, clamping scores to [0.0, 1.0]."""
        results: list[RelevanceResult] = []
        for item in response.get("results", []):
            raw_score = float(item.get("relevance_score", 0.0))
            clamped_score = max(0.0, min(1.0, raw_score))
            results.append(
                RelevanceResult(
                    chapter_id=item.get("chapter_id", ""),
                    chapter_title=item.get("chapter_title", ""),
                    relevance_score=clamped_score,
                    matched_topics=item.get("matched_topics", []),
                    reasoning=item.get("reasoning"),
                )
            )
        return results
