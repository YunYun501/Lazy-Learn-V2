import json

CROSS_SECTION_RELATIONSHIP_PROMPT = """
You are analyzing relationships between STEM concepts across sections to build a knowledge graph.

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
- variant_of: Concept A is an alternative approach to the same problem as Concept B
- contains: Concept A is a conceptual grouping that contains Concept B

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

KEY_RESULT_EXTRACTION_PROMPT = """
You are analyzing a specific section of a STEM textbook to extract ONLY key theorems, methods, formulas, definitions, and results.

Section: {section_title}
Section Path: {section_path}
Parent Topic: {parent_concept}

Section Content:
{section_text}

Equations in this section:
{equations_text}

First identify 1-3 conceptual groups (themes) that organize the key results in this section.
Then, for each group, list 1-6 specific members (the actual named theorems, methods, formulas, or definitions).
Then, identify intra-group relationships between members of the same group.

Guidelines:
- Only include the most important named results a student needs to know.
- Do NOT list every equation or minor concept.
- Use relationship_type "variant_of" when members are alternative approaches to the same problem.
- Intra-group relationships must reference member titles within the same group.
- Keep derivations only for step-by-step mathematical derivation chains.

Return a JSON object with this exact structure:
{{
  "concept_groups": [
    {{
      "name": "group name (e.g. Fatigue Failure Criteria)",
      "description": "what this group covers",
      "node_type": "concept",
      "members": [
        {{
          "title": "specific method/theorem/formula name",
          "node_type": "method|theorem|result|definition|formula|concept",
          "defining_equation": "LaTeX string or empty",
          "description": "1-2 sentences"
        }}
      ],
      "intra_relationships": [
        {{
          "source": "member title",
          "target": "member title",
          "relationship_type": "variant_of|derives_from|equivalent_form|generalizes|specializes",
          "reasoning": "brief explanation"
        }}
      ]
    }}
  ],
  "derivations": [
    {{
      "source": "source result title",
      "target": "target result title",
      "description": "how source leads to target",
      "derivation_steps": ["step 1 LaTeX", "step 2 LaTeX"]
    }}
  ]
}}

Example: In a section about fatigue failure criteria:
- Concept group: "Fatigue Failure Criteria" (concept) with members:
  - "Soderberg Criterion" (formula) — \\frac{{\\sigma_a}}{{\\sigma_e}} + \\frac{{\\sigma_m}}{{\\sigma_y}} = 1
  - "Goodman Criterion" (formula) — \\frac{{\\sigma_a}}{{\\sigma_e}} + \\frac{{\\sigma_m}}{{\\sigma_{{ult}}}} = 1
  - "Gerber Criterion" (formula) — \\frac{{\\sigma_a}}{{\\sigma_e}} + \\left(\\frac{{\\sigma_m}}{{\\sigma_{{ult}}}}\\right)^2 = 1
  - "ASME Elliptic Criterion" (formula) — \\left(\\frac{{\\sigma_a}}{{\\sigma_e}}\\right)^2 + \\left(\\frac{{\\sigma_m}}{{\\sigma_y}}\\right)^2 = 1
- Intra-group relationships:
  - Soderberg Criterion variant_of Goodman Criterion (alternative safety criterion)
  - Gerber Criterion variant_of Goodman Criterion (nonlinear alternative)
  - ASME Elliptic Criterion variant_of Soderberg Criterion (elliptic variant)

IMPORTANT: Return ONLY valid JSON. The root must be an object with "concept_groups" and "derivations" arrays.
Do not include markdown or code blocks.
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


def parse_relationship_response(raw: str) -> list[dict]:
    try:
        stripped = _strip_code_blocks(raw)
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            relationships = parsed.get("relationships")
            if isinstance(relationships, list):
                return relationships
        return []
    except (json.JSONDecodeError, ValueError):
        return []


def parse_key_result_response(raw) -> dict:
    try:

        def normalize_concept_groups(parsed: dict) -> list[dict]:
            concept_groups = parsed.get("concept_groups")
            if isinstance(concept_groups, list):
                return concept_groups
            key_results = parsed.get("key_results")
            if isinstance(key_results, list):
                section_name = (
                    parsed.get("section_title")
                    or parsed.get("section")
                    or parsed.get("section_path")
                    or "Section"
                )
                description = (
                    f"Key results extracted from {section_name}."
                    if section_name != "Section"
                    else "Key results extracted from section."
                )
                return [
                    {
                        "name": section_name,
                        "description": description,
                        "node_type": "concept",
                        "members": key_results,
                        "intra_relationships": [],
                    }
                ]
            return []

        if isinstance(raw, dict):
            return {
                "concept_groups": normalize_concept_groups(raw),
                "derivations": raw.get("derivations", []),
            }
        if isinstance(raw, str):
            stripped = _strip_code_blocks(raw)
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return {
                    "concept_groups": normalize_concept_groups(parsed),
                    "derivations": parsed.get("derivations", []),
                }
        return {"concept_groups": [], "derivations": []}
    except (json.JSONDecodeError, ValueError):
        return {"concept_groups": [], "derivations": []}
