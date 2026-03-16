import json

CONCEPT_EXTRACTION_PROMPT = """
You are analyzing a STEM textbook chapter to extract concepts and their types.

Chapter: {chapter_title}
Chapter Number: {chapter_number}

Key Concepts Already Identified:
{key_concepts}

Prerequisites:
{prerequisites}

Has Mathematical Content: {mathematical_content}

Chapter Content (excerpt):
{chapter_content}

Extract these concepts as structured graph nodes. For each concept:
- Classify its type: theorem, definition, equation, lemma, concept, or example
- Write a brief description (1-2 sentences)
- Identify any aliases or alternative names

Return a JSON object with this exact structure:
{{
  "concepts": [
    {{
      "title": "concept name",
      "node_type": "theorem|definition|equation|lemma|concept|example",
      "description": "brief description",
      "aliases": ["alt name 1", "alt name 2"]
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON. The root must be an object with a "concepts" array.
Use only these node_type values: theorem, definition, equation, lemma, concept, example
"""

RELATIONSHIP_EXTRACTION_PROMPT = """
You are analyzing relationships between STEM concepts to build a knowledge graph.

Textbook: {textbook_title}

Concepts to analyze:
{concepts_list}

For each pair of related concepts, identify the relationship type.

Available relationship types:
- derives_from: Concept A is mathematically derived from Concept B
- proves: Proof A proves Theorem B
- prerequisite_of: Understanding A is required before B
- uses: Concept A uses or applies Concept B
- generalizes: Concept A is a generalization of Concept B
- specializes: Concept A is a special case of Concept B
- contradicts: Concept A contradicts or is in tension with Concept B
- defines: Definition A formally defines Term B
- equivalent_form: A and B are equivalent representations (e.g., equivalent circuits)

Return a JSON object with this exact structure:
{{
  "relationships": [
    {{
      "source": "concept title",
      "target": "concept title",
      "relationship_type": "one of the types above",
      "confidence": 0.0-1.0,
      "reasoning": "brief explanation"
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON. The root must be an object with a "relationships" array.
Only use the exact relationship_type values listed above.
"""


def _strip_code_blocks(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[:-3].rstrip()
    return stripped


def parse_concept_extraction_response(raw: str) -> list[dict]:
    try:
        stripped = _strip_code_blocks(raw)
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return parsed
        return []
    except (json.JSONDecodeError, ValueError):
        return []


def parse_relationship_response(raw: str) -> list[dict]:
    try:
        stripped = _strip_code_blocks(raw)
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return parsed
        return []
    except (json.JSONDecodeError, ValueError):
        return []
