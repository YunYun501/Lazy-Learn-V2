import json
from app.services.knowledge_graph_prompts import (
    CONCEPT_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
    parse_concept_extraction_response,
    parse_relationship_response,
    _strip_code_blocks,
)


class TestPromptRendering:
    def test_concept_prompt_renders_with_data(self):
        rendered = CONCEPT_EXTRACTION_PROMPT.format(
            chapter_title="The Z-Transform",
            chapter_number="3",
            key_concepts="Causality, Stability, Region of Convergence",
            prerequisites="Fourier Transform, Complex Numbers",
            mathematical_content=True,
            chapter_content="The Z-transform converts a discrete-time signal into a complex frequency-domain representation.",
        )
        assert "The Z-Transform" in rendered
        assert "Chapter Number: 3" in rendered
        assert "Causality, Stability, Region of Convergence" in rendered
        assert "Fourier Transform, Complex Numbers" in rendered
        assert "True" in rendered
        assert "node_type" in rendered
        assert "theorem|definition|equation|lemma|concept|example" in rendered

    def test_relationship_prompt_renders_with_data(self):
        concepts_list = "1. Z-Transform\n2. Fourier Transform\n3. Causality"
        rendered = RELATIONSHIP_EXTRACTION_PROMPT.format(
            textbook_title="Digital Signal Processing",
            concepts_list=concepts_list,
        )
        assert "Digital Signal Processing" in rendered
        assert "Z-Transform" in rendered
        assert "derives_from" in rendered
        assert "prerequisite_of" in rendered
        assert "confidence" in rendered


class TestConceptExtractionParser:
    def test_parse_concept_response_valid_json(self):
        valid_json = json.dumps(
            [
                {
                    "title": "Z-Transform",
                    "node_type": "definition",
                    "description": "A mathematical transform for discrete-time signals.",
                    "aliases": ["ZT", "bilateral Z-transform"],
                },
                {
                    "title": "Causality",
                    "node_type": "concept",
                    "description": "A system property where output depends only on past inputs.",
                    "aliases": [],
                },
            ]
        )
        result = parse_concept_extraction_response(valid_json)
        assert len(result) == 2
        assert result[0]["title"] == "Z-Transform"
        assert result[0]["node_type"] == "definition"
        assert result[1]["title"] == "Causality"

    def test_parse_concept_response_markdown_wrapped(self):
        markdown_json = """```json
[
  {
    "title": "Stability",
    "node_type": "theorem",
    "description": "A system is stable if bounded inputs produce bounded outputs.",
    "aliases": ["BIBO stability"]
  }
]
```"""
        result = parse_concept_extraction_response(markdown_json)
        assert len(result) == 1
        assert result[0]["title"] == "Stability"
        assert result[0]["node_type"] == "theorem"

    def test_parse_concept_response_invalid_json(self):
        result = parse_concept_extraction_response("this is not valid json at all")
        assert result == []
        assert isinstance(result, list)

    def test_parse_concept_response_malformed_json(self):
        result = parse_concept_extraction_response('{"title": "incomplete')
        assert result == []

    def test_parse_concept_response_empty_string(self):
        result = parse_concept_extraction_response("")
        assert result == []

    def test_parse_concept_response_not_array(self):
        not_array = json.dumps({"title": "Single object, not array"})
        result = parse_concept_extraction_response(not_array)
        assert result == []


class TestRelationshipExtractionParser:
    def test_parse_relationship_response_valid_json(self):
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

    def test_parse_relationship_response_invalid_json(self):
        result = parse_relationship_response("not json")
        assert result == []

    def test_parse_relationship_response_empty_array(self):
        result = parse_relationship_response(json.dumps([]))
        assert result == []


class TestStripCodeBlocks:
    def test_strip_code_blocks_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = _strip_code_blocks(text)
        assert result == '{"key": "value"}'

    def test_strip_code_blocks_plain_fence(self):
        text = "```\n[1, 2, 3]\n```"
        result = _strip_code_blocks(text)
        assert result == "[1, 2, 3]"

    def test_strip_code_blocks_no_fence(self):
        text = '{"key": "value"}'
        result = _strip_code_blocks(text)
        assert result == '{"key": "value"}'
