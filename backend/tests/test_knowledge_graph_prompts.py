import json
from app.services.knowledge_graph_prompts import (
    CROSS_SECTION_RELATIONSHIP_PROMPT,
    KEY_RESULT_EXTRACTION_PROMPT,
    parse_key_result_response,
    parse_relationship_response,
    _strip_code_blocks,
)


class TestPromptRendering:
    def test_key_result_prompt_renders_with_data(self):
        rendered = KEY_RESULT_EXTRACTION_PROMPT.format(
            section_title="Fatigue Criteria",
            section_path="CH7/7.5",
            parent_concept="Shafts",
            section_text="The Soderberg line relates alternating and mean stress.",
            equations_text="\\frac{{S_a}}{{S_e}} + \\frac{{S_m}}{{S_y}} = 1",
        )
        assert "Fatigue Criteria" in rendered
        assert "CH7/7.5" in rendered
        assert "Shafts" in rendered
        assert "concept_groups" in rendered
        assert "derivations" in rendered
        assert "variant_of" in rendered

    def test_cross_section_prompt_renders_with_data(self):
        concepts_list = "1. Soderberg Line\n2. Goodman Line\n3. Gerber Line"
        rendered = CROSS_SECTION_RELATIONSHIP_PROMPT.format(
            textbook_title="Mechanical Design",
            concepts_list=concepts_list,
        )
        assert "Mechanical Design" in rendered
        assert "Soderberg Line" in rendered
        assert "derives_from" in rendered
        assert "prerequisite_of" in rendered
        assert "variant_of" in rendered
        assert "contains" in rendered
        assert "confidence" in rendered


class TestKeyResultParser:
    def test_parse_concept_groups_valid_dict(self):
        valid = {
            "concept_groups": [
                {
                    "name": "Fatigue Criteria",
                    "description": "Alternative failure criteria",
                    "node_type": "concept",
                    "members": [
                        {
                            "title": "Soderberg Line",
                            "node_type": "formula",
                            "defining_equation": "Sa/Se + Sm/Sy = 1",
                            "description": "Conservative criterion",
                        }
                    ],
                    "intra_relationships": [],
                }
            ],
            "derivations": [],
        }
        result = parse_key_result_response(valid)
        assert len(result["concept_groups"]) == 1
        assert result["concept_groups"][0]["name"] == "Fatigue Criteria"
        assert len(result["concept_groups"][0]["members"]) == 1
        assert result["concept_groups"][0]["members"][0]["title"] == "Soderberg Line"

    def test_parse_concept_groups_valid_json_string(self):
        valid_json = json.dumps(
            {
                "concept_groups": [
                    {
                        "name": "Test Group",
                        "description": "desc",
                        "node_type": "concept",
                        "members": [],
                        "intra_relationships": [],
                    }
                ],
                "derivations": [],
            }
        )
        result = parse_key_result_response(valid_json)
        assert len(result["concept_groups"]) == 1
        assert result["concept_groups"][0]["name"] == "Test Group"

    def test_parse_legacy_key_results_fallback(self):
        legacy = {
            "key_results": [
                {
                    "title": "Critical Speed",
                    "node_type": "formula",
                    "defining_equation": "omega_c",
                    "description": "Natural frequency",
                }
            ],
            "derivations": [],
        }
        result = parse_key_result_response(legacy)
        assert len(result["concept_groups"]) == 1
        assert len(result["concept_groups"][0]["members"]) == 1
        assert result["concept_groups"][0]["members"][0]["title"] == "Critical Speed"

    def test_parse_invalid_json_returns_empty(self):
        result = parse_key_result_response("this is not valid json")
        assert result == {"concept_groups": [], "derivations": []}

    def test_parse_empty_string_returns_empty(self):
        result = parse_key_result_response("")
        assert result == {"concept_groups": [], "derivations": []}

    def test_parse_malformed_json_returns_empty(self):
        result = parse_key_result_response('{"concept_groups": [incomplete')
        assert result == {"concept_groups": [], "derivations": []}

    def test_parse_markdown_wrapped_json(self):
        markdown = """```json
{
  "concept_groups": [
    {
      "name": "Wrapped",
      "description": "test",
      "node_type": "concept",
      "members": [],
      "intra_relationships": []
    }
  ],
  "derivations": []
}
```"""
        result = parse_key_result_response(markdown)
        assert len(result["concept_groups"]) == 1
        assert result["concept_groups"][0]["name"] == "Wrapped"

    def test_parse_with_derivations(self):
        data = {
            "concept_groups": [
                {
                    "name": "Group",
                    "description": "desc",
                    "node_type": "concept",
                    "members": [
                        {
                            "title": "A",
                            "node_type": "method",
                            "defining_equation": "",
                            "description": "",
                        },
                        {
                            "title": "B",
                            "node_type": "formula",
                            "defining_equation": "",
                            "description": "",
                        },
                    ],
                    "intra_relationships": [],
                }
            ],
            "derivations": [
                {
                    "source": "A",
                    "target": "B",
                    "description": "A leads to B",
                    "derivation_steps": ["step 1", "step 2"],
                }
            ],
        }
        result = parse_key_result_response(data)
        assert len(result["derivations"]) == 1
        assert result["derivations"][0]["source"] == "A"
        assert len(result["derivations"][0]["derivation_steps"]) == 2

    def test_parse_with_intra_relationships(self):
        data = {
            "concept_groups": [
                {
                    "name": "Criteria",
                    "description": "desc",
                    "node_type": "concept",
                    "members": [
                        {
                            "title": "Soderberg",
                            "node_type": "formula",
                            "defining_equation": "",
                            "description": "",
                        },
                        {
                            "title": "Goodman",
                            "node_type": "formula",
                            "defining_equation": "",
                            "description": "",
                        },
                    ],
                    "intra_relationships": [
                        {
                            "source": "Soderberg",
                            "target": "Goodman",
                            "relationship_type": "variant_of",
                            "reasoning": "Alternative criterion",
                        }
                    ],
                }
            ],
            "derivations": [],
        }
        result = parse_key_result_response(data)
        rels = result["concept_groups"][0]["intra_relationships"]
        assert len(rels) == 1
        assert rels[0]["relationship_type"] == "variant_of"


class TestRelationshipParser:
    def test_parse_valid_json_list(self):
        valid_json = json.dumps(
            [
                {
                    "source": "Z-Transform",
                    "target": "Fourier Transform",
                    "relationship_type": "derives_from",
                    "confidence": 0.95,
                    "reasoning": "Z-transform generalizes Fourier transform.",
                },
            ]
        )
        result = parse_relationship_response(valid_json)
        assert len(result) == 1
        assert result[0]["source"] == "Z-Transform"
        assert result[0]["relationship_type"] == "derives_from"

    def test_parse_dict_with_relationships_key(self):
        valid_json = json.dumps(
            {
                "relationships": [
                    {
                        "source": "A",
                        "target": "B",
                        "relationship_type": "uses",
                        "confidence": 0.8,
                        "reasoning": "A uses B",
                    }
                ]
            }
        )
        result = parse_relationship_response(valid_json)
        assert len(result) == 1
        assert result[0]["source"] == "A"

    def test_parse_invalid_json_returns_empty(self):
        result = parse_relationship_response("not json")
        assert result == []

    def test_parse_empty_array(self):
        result = parse_relationship_response(json.dumps([]))
        assert result == []


class TestStripCodeBlocks:
    def test_strip_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = _strip_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_strip_plain_fence(self):
        text = "```\n[1, 2, 3]\n```"
        result = _strip_code_blocks(text)
        assert result == "[1, 2, 3]"

    def test_no_fence_unchanged(self):
        text = '{"key": "value"}'
        result = _strip_code_blocks(text)
        assert result == '{"key": "value"}'
