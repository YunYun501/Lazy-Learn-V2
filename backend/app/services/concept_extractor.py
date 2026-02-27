import json

from app.models.ai_models import ConceptExtraction

# Constant system prompt for DeepSeek cache hit optimization.
# MUST remain identical across all calls — 10x cheaper ($0.028/M vs $0.28/M tokens).
CONCEPT_EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert STEM tutor assistant for the Lazy Learn study application. "
    "You help students understand complex technical concepts by analyzing textbook content. "
    "Always be precise, use proper mathematical notation, and cite sources when possible.\n\n"
    "Analyze the student's question and extract:\n"
    "1) Named concepts/theorems/transforms mentioned explicitly (e.g., 'Z-transform', 'Laplace')\n"
    "2) Concepts IMPLIED by equations — recognize equation FORMS regardless of specific variable values. "
    "E.g., Y(z)=az/(z-b) is a Z-transform expression even if a and b are different numbers.\n"
    "3) Related prerequisite concepts that may help understand this topic.\n"
    "Return JSON: "
    "{\"concepts\": [\"concept1\", \"concept2\"], "
    "\"equations\": [\"equation form 1\"], "
    "\"related_terms\": [\"alias1\", \"alias2\"]}"
)


class ConceptExtractor:
    """Step 0 of the hybrid search pipeline: extract concepts from a user query."""

    def __init__(self, deepseek_provider):
        self.provider = deepseek_provider

    async def extract(self, query: str) -> ConceptExtraction:
        """Extract concepts and equation forms from a student's query.

        Recognises equation FORMS — Y(z)=0.5z/(z-0.8) is identified as a
        Z-transform even though the specific values differ from any textbook example.
        """
        messages = [
            {"role": "system", "content": CONCEPT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        json_str = await self.provider.chat(messages, json_mode=True)
        parsed = json.loads(json_str)
        return ConceptExtraction(
            concepts=parsed.get("concepts", []),
            equations=parsed.get("equations", []),
        )
