"""Step 2 of the hybrid search pipeline: AI categorization of EXPLAINS vs USES.

Takes keyword search hits (Task 14) and uses DeepSeek to classify whether
each chapter EXPLAINS or USES the concept the student is asking about.
"""
import json

from app.models.ai_models import ClassifiedMatch
from app.services.keyword_search import SearchHit

# Constant system prompt for DeepSeek cache hit optimization.
CATEGORIZATION_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "For each chapter description provided, classify whether the chapter EXPLAINS or USES the given concept.\n"
    "EXPLAINS = the chapter introduces, derives, defines, or proves the concept.\n"
    "USES = the chapter applies the concept in examples, problems, or further topics without explaining it.\n"
    "Be precise: a chapter that has one equation using Z-transform but is mainly about stability analysis "
    "should be classified as USES, not EXPLAINS.\n"
    "Return JSON: "
    "{\"classification\": \"EXPLAINS|USES\", \"confidence\": 0.0-1.0, \"reason\": \"brief reason\"}"
)

CONFIDENCE_THRESHOLD = 0.3  # Filter out low-confidence matches


class MatchCategorizer:
    """Step 2: AI categorization of search hits as EXPLAINS or USES."""

    def __init__(self, deepseek_provider):
        self.provider = deepseek_provider

    async def categorize(
        self,
        matches: list[SearchHit],
        concept: str,
    ) -> list[ClassifiedMatch]:
        """Classify each search hit as EXPLAINS or USES for the given concept.

        Results are sorted: EXPLAINS first (students usually want explanations),
        then USES, both sorted by confidence descending.
        Low-confidence matches (< CONFIDENCE_THRESHOLD) are filtered out.
        """
        results: list[ClassifiedMatch] = []

        for hit in matches:
            messages = [
                {"role": "system", "content": CATEGORIZATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Concept: {concept}\n\n"
                        f"Chapter description:\n{hit.content}"
                    ),
                },
            ]
            json_str = await self.provider.chat(messages, json_mode=True)
            parsed = json.loads(json_str)

            classification = parsed.get("classification", "USES")
            if classification not in ("EXPLAINS", "USES"):
                classification = "USES"

            confidence = float(parsed.get("confidence", 0.5))
            if confidence < CONFIDENCE_THRESHOLD:
                continue

            results.append(
                ClassifiedMatch(
                    source=hit.source_textbook,
                    chapter=hit.chapter,
                    subchapter="",
                    classification=classification,
                    confidence=confidence,
                    reason=parsed.get("reason", ""),
                )
            )

        # Sort: EXPLAINS first, then USES; within each group by confidence desc
        results.sort(
            key=lambda m: (0 if m.classification == "EXPLAINS" else 1, -m.confidence)
        )
        return results
