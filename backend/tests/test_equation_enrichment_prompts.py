import json
import pytest
from backend.app.services.knowledge_graph_prompts import (
    EQUATION_ENRICHMENT_PROMPT,
    parse_enrichment_response,
)


class TestEquationEnrichmentPrompt:
    """Test the EQUATION_ENRICHMENT_PROMPT template."""

    def test_prompt_has_equation_latex_placeholder(self):
        """Prompt must have {equation_latex} placeholder."""
        assert "{equation_latex}" in EQUATION_ENRICHMENT_PROMPT

    def test_prompt_has_section_text_placeholder(self):
        """Prompt must have {section_text} placeholder."""
        assert "{section_text}" in EQUATION_ENRICHMENT_PROMPT

    def test_prompt_has_existing_nodes_placeholder(self):
        """Prompt must have {existing_nodes_json} placeholder."""
        assert "{existing_nodes_json}" in EQUATION_ENRICHMENT_PROMPT

    def test_prompt_is_string(self):
        """Prompt must be a string."""
        assert isinstance(EQUATION_ENRICHMENT_PROMPT, str)

    def test_prompt_mentions_json_requirement(self):
        """Prompt should instruct to return JSON only."""
        assert (
            "JSON" in EQUATION_ENRICHMENT_PROMPT or "json" in EQUATION_ENRICHMENT_PROMPT
        )


class TestParseEnrichmentResponse:
    """Test parse_enrichment_response() function."""

    def test_parse_valid_dict_input(self):
        """Parse dict with equation_components key."""
        raw = {
            "equation_components": [
                {
                    "symbol": "k_a",
                    "name": "surface factor",
                    "type": "constant",
                    "description": "Accounts for surface finish",
                    "latex": None,
                    "page_reference": "p.312",
                    "linked_node_id": None,
                }
            ]
        }
        result = parse_enrichment_response(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["symbol"] == "k_a"
        assert result[0]["type"] == "constant"

    def test_parse_valid_json_string(self):
        """Parse JSON string with equation_components."""
        raw = json.dumps(
            {
                "equation_components": [
                    {
                        "symbol": "\\sigma'_e",
                        "name": "endurance limit",
                        "type": "calculated",
                        "description": "Base endurance limit",
                        "latex": "\\sigma'_e \\approx 0.5 S_{ut}",
                        "page_reference": None,
                        "linked_node_id": "uuid-123",
                    }
                ]
            }
        )
        result = parse_enrichment_response(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["symbol"] == "\\sigma'_e"
        assert result[0]["type"] == "calculated"
        assert result[0]["linked_node_id"] == "uuid-123"

    def test_parse_json_in_code_block(self):
        """Parse JSON wrapped in markdown code block."""
        raw = """```json
{
  "equation_components": [
    {
      "symbol": "k_b",
      "name": "size factor",
      "type": "constant",
      "description": "Size effect on fatigue",
      "latex": null,
      "page_reference": "p.315",
      "linked_node_id": null
    }
  ]
}
```"""
        result = parse_enrichment_response(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["symbol"] == "k_b"

    def test_parse_direct_list_input(self):
        """Parse list directly (no equation_components wrapper)."""
        raw = [
            {
                "symbol": "k_c",
                "name": "load factor",
                "type": "constant",
                "description": "Load type effect",
                "latex": None,
                "page_reference": "p.318",
                "linked_node_id": None,
            }
        ]
        result = parse_enrichment_response(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["symbol"] == "k_c"

    def test_parse_malformed_json_returns_empty(self):
        """Malformed JSON returns empty list."""
        result = parse_enrichment_response("not valid json at all")
        assert result == []

    def test_parse_none_returns_empty(self):
        """None input returns empty list."""
        result = parse_enrichment_response(None)
        assert result == []

    def test_parse_empty_string_returns_empty(self):
        """Empty string returns empty list."""
        result = parse_enrichment_response("")
        assert result == []

    def test_parse_incomplete_json_returns_empty(self):
        """Incomplete JSON returns empty list."""
        result = parse_enrichment_response('{"equation_components": [incomplete')
        assert result == []

    def test_parse_component_has_required_keys(self):
        """Each component must have required keys."""
        raw = {
            "equation_components": [
                {
                    "symbol": "F",
                    "name": "force",
                    "type": "calculated",
                    "description": "Applied force",
                    "latex": "F = ma",
                    "page_reference": "p.10",
                    "linked_node_id": "uuid-456",
                }
            ]
        }
        result = parse_enrichment_response(raw)
        component = result[0]
        required_keys = {
            "symbol",
            "name",
            "type",
            "description",
            "latex",
            "page_reference",
            "linked_node_id",
        }
        assert all(key in component for key in required_keys)

    def test_parse_multiple_components(self):
        """Parse multiple equation components."""
        raw = {
            "equation_components": [
                {
                    "symbol": "a",
                    "name": "acceleration",
                    "type": "calculated",
                    "description": "Rate of change of velocity",
                    "latex": "a = dv/dt",
                    "page_reference": None,
                    "linked_node_id": "uuid-1",
                },
                {
                    "symbol": "v",
                    "name": "velocity",
                    "type": "calculated",
                    "description": "Rate of change of position",
                    "latex": "v = dx/dt",
                    "page_reference": None,
                    "linked_node_id": "uuid-2",
                },
                {
                    "symbol": "m",
                    "name": "mass",
                    "type": "constant",
                    "description": "Inertial property",
                    "latex": None,
                    "page_reference": "p.5",
                    "linked_node_id": None,
                },
            ]
        }
        result = parse_enrichment_response(raw)
        assert len(result) == 3
        assert result[0]["symbol"] == "a"
        assert result[1]["symbol"] == "v"
        assert result[2]["symbol"] == "m"

    def test_parse_type_values_preserved(self):
        """Type values (constant/calculated) are preserved."""
        raw = {
            "equation_components": [
                {
                    "symbol": "x",
                    "name": "test",
                    "type": "constant",
                    "description": "desc",
                    "latex": None,
                    "page_reference": None,
                    "linked_node_id": None,
                },
                {
                    "symbol": "y",
                    "name": "test2",
                    "type": "calculated",
                    "description": "desc",
                    "latex": "y = f(x)",
                    "page_reference": None,
                    "linked_node_id": None,
                },
            ]
        }
        result = parse_enrichment_response(raw)
        assert result[0]["type"] == "constant"
        assert result[1]["type"] == "calculated"
