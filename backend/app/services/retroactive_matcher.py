"""Retroactive matcher — triggers relevance matching when materials are uploaded to a course."""

from app.models.pipeline_models import PipelineStatus, RelevanceResult
from app.services.relevance_matcher import RelevanceMatcher
from app.services.storage import MetadataStore

QUALIFYING_STATUSES = frozenset({
    PipelineStatus.toc_extracted.value,
    PipelineStatus.awaiting_verification.value,
    PipelineStatus.extracting.value,
    PipelineStatus.partially_extracted.value,
    PipelineStatus.fully_extracted.value,
})


class RetroactiveMatcher:
    """Thin coordinator that calls RelevanceMatcher for each qualifying textbook in a course."""

    def __init__(self, store: MetadataStore, relevance_matcher: RelevanceMatcher) -> None:
        self.store = store
        self.relevance_matcher = relevance_matcher

    async def on_material_summarized(self, course_id: str) -> dict[str, list[RelevanceResult]]:
        """Run relevance matching for all qualifying textbooks in the course.

        A textbook qualifies if its pipeline_status is past 'uploaded' (i.e. TOC exists).
        Returns results keyed by textbook_id. Empty dict if no qualifying textbooks.
        """
        textbooks = await self.store.get_course_textbooks(course_id)
        qualifying = [
            tb for tb in textbooks
            if tb.get("pipeline_status") in QUALIFYING_STATUSES
        ]

        if not qualifying:
            return {}

        results: dict[str, list[RelevanceResult]] = {}
        for tb in qualifying:
            tb_id = tb["id"]
            results[tb_id] = await self.relevance_matcher.match_chapters(tb_id, course_id)

        return results
