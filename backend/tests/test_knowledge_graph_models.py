"""Tests for knowledge graph models."""

import pytest
from pydantic import ValidationError
from app.models.knowledge_graph_models import (
    NodeType,
    RelationshipType,
    GraphJobStatus,
    NodeLevel,
    ConceptNode,
    ConceptEdge,
    GraphData,
    BuildGraphRequest,
    BuildGraphResponse,
    GraphStatusResponse,
    ConceptNodeDetail,
)


class TestNodeTypeEnum:
    """Test NodeType enum values."""

    def test_node_type_enum_values(self):
        """Verify all 29 NodeType values exist."""
        expected = {
            "theorem",
            "definition",
            "equation",
            "lemma",
            "corollary",
            "axiom",
            "proof",
            "identity",
            "formula",
            "law",
            "principle",
            "theory",
            "hypothesis",
            "observation",
            "constant",
            "property",
            "method",
            "technique",
            "algorithm",
            "procedure",
            "criterion",
            "model",
            "approximation",
            "rule",
            "condition",
            "relation",
            "concept",
            "result",
            "example",
        }
        actual = {e.value for e in NodeType}
        assert actual == expected
        assert len(NodeType) == 29


class TestRelationshipTypeEnum:
    """Test RelationshipType enum values."""

    def test_relationship_type_enum_values(self):
        """Verify all 11 RelationshipType values exist."""
        assert RelationshipType.derives_from.value == "derives_from"
        assert RelationshipType.proves.value == "proves"
        assert RelationshipType.prerequisite_of.value == "prerequisite_of"
        assert RelationshipType.uses.value == "uses"
        assert RelationshipType.generalizes.value == "generalizes"
        assert RelationshipType.specializes.value == "specializes"
        assert RelationshipType.contradicts.value == "contradicts"
        assert RelationshipType.defines.value == "defines"
        assert RelationshipType.equivalent_form.value == "equivalent_form"
        assert RelationshipType.variant_of.value == "variant_of"
        assert RelationshipType.contains.value == "contains"
        assert len(RelationshipType) == 11


class TestGraphJobStatusEnum:
    """Test GraphJobStatus enum values."""

    def test_graph_job_status_enum_values(self):
        """Verify all 4 GraphJobStatus values exist."""
        assert GraphJobStatus.pending.value == "pending"
        assert GraphJobStatus.processing.value == "processing"
        assert GraphJobStatus.completed.value == "completed"
        assert GraphJobStatus.failed.value == "failed"
        assert len(GraphJobStatus) == 4


class TestNodeLevelEnum:
    """Test NodeLevel enum values."""

    def test_node_level_enum_values(self):
        """Verify all 3 NodeLevel values exist."""
        assert NodeLevel.chapter.value == "chapter"
        assert NodeLevel.section.value == "section"
        assert NodeLevel.subsection.value == "subsection"
        assert len(NodeLevel) == 3


class TestConceptNodeModel:
    """Test ConceptNode model validation and serialization."""

    def test_concept_node_required_fields(self):
        """Verify ConceptNode enforces required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ConceptNode()
        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check that id, textbook_id, title, node_type, level, created_at are required
        error_fields = {e["loc"][0] for e in errors}
        assert "id" in error_fields
        assert "textbook_id" in error_fields
        assert "title" in error_fields
        assert "node_type" in error_fields
        assert "level" in error_fields
        assert "created_at" in error_fields

    def test_concept_node_valid_creation(self):
        """Create a valid ConceptNode."""
        node = ConceptNode(
            id="node_1",
            textbook_id="textbook_1",
            title="Pythagorean Theorem",
            description="A fundamental theorem in geometry",
            node_type=NodeType.theorem,
            level=NodeLevel.section,
            source_chapter_id="ch_1",
            source_section_id="sec_1",
            source_page=42,
            metadata={"latex": "a^2 + b^2 = c^2"},
            created_at="2025-03-16T10:00:00Z",
        )
        assert node.id == "node_1"
        assert node.textbook_id == "textbook_1"
        assert node.title == "Pythagorean Theorem"
        assert node.node_type == NodeType.theorem
        assert node.level == NodeLevel.section
        assert node.metadata == {"latex": "a^2 + b^2 = c^2"}

    def test_concept_node_optional_fields(self):
        """ConceptNode with only required fields."""
        node = ConceptNode(
            id="node_2",
            textbook_id="textbook_1",
            title="Derivative",
            node_type=NodeType.definition,
            level=NodeLevel.chapter,
            created_at="2025-03-16T10:00:00Z",
        )
        assert node.description is None
        assert node.source_chapter_id is None
        assert node.source_section_id is None
        assert node.source_page is None
        assert node.metadata is None

    def test_concept_node_json_serialization(self):
        """ConceptNode serializes to valid JSON."""
        node = ConceptNode(
            id="node_3",
            textbook_id="textbook_1",
            title="Integration",
            node_type=NodeType.concept,
            level=NodeLevel.section,
            created_at="2025-03-16T10:00:00Z",
        )
        json_str = node.model_dump_json()
        assert isinstance(json_str, str)
        assert "node_3" in json_str
        assert "textbook_1" in json_str
        assert "Integration" in json_str
        assert "concept" in json_str


class TestConceptEdgeModel:
    """Test ConceptEdge model validation."""

    def test_concept_edge_required_fields(self):
        """Verify ConceptEdge enforces required fields."""
        with pytest.raises(ValidationError) as exc_info:
            ConceptEdge()
        errors = exc_info.value.errors()
        error_fields = {e["loc"][0] for e in errors}
        assert "id" in error_fields
        assert "textbook_id" in error_fields
        assert "source_node_id" in error_fields
        assert "target_node_id" in error_fields
        assert "relationship_type" in error_fields
        assert "created_at" in error_fields

    def test_concept_edge_valid_creation(self):
        """Create a valid ConceptEdge."""
        edge = ConceptEdge(
            id="edge_1",
            textbook_id="textbook_1",
            source_node_id="node_1",
            target_node_id="node_2",
            relationship_type=RelationshipType.prerequisite_of,
            confidence=0.95,
            reasoning="Node 1 must be understood before Node 2",
            created_at="2025-03-16T10:00:00Z",
        )
        assert edge.id == "edge_1"
        assert edge.source_node_id == "node_1"
        assert edge.target_node_id == "node_2"
        assert edge.relationship_type == RelationshipType.prerequisite_of
        assert edge.confidence == 0.95

    def test_concept_edge_default_confidence(self):
        """ConceptEdge defaults confidence to 1.0."""
        edge = ConceptEdge(
            id="edge_2",
            textbook_id="textbook_1",
            source_node_id="node_1",
            target_node_id="node_2",
            relationship_type=RelationshipType.uses,
            created_at="2025-03-16T10:00:00Z",
        )
        assert edge.confidence == 1.0

    def test_invalid_relationship_type_rejected(self):
        """ConceptEdge rejects invalid relationship_type."""
        with pytest.raises(ValidationError) as exc_info:
            ConceptEdge(
                id="edge_3",
                textbook_id="textbook_1",
                source_node_id="node_1",
                target_node_id="node_2",
                relationship_type="invalid_type",  # type: ignore
                created_at="2025-03-16T10:00:00Z",
            )
        errors = exc_info.value.errors()
        assert any("relationship_type" in str(e) for e in errors)


class TestGraphDataModel:
    """Test GraphData model."""

    def test_graph_data_creation(self):
        """Create a GraphData with nodes and edges."""
        node = ConceptNode(
            id="node_1",
            textbook_id="textbook_1",
            title="Theorem",
            node_type=NodeType.theorem,
            level=NodeLevel.section,
            created_at="2025-03-16T10:00:00Z",
        )
        edge = ConceptEdge(
            id="edge_1",
            textbook_id="textbook_1",
            source_node_id="node_1",
            target_node_id="node_2",
            relationship_type=RelationshipType.proves,
            created_at="2025-03-16T10:00:00Z",
        )
        graph = GraphData(
            textbook_id="textbook_1",
            nodes=[node],
            edges=[edge],
        )
        assert graph.textbook_id == "textbook_1"
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1

    def test_graph_data_empty_defaults(self):
        """GraphData defaults to empty nodes and edges."""
        graph = GraphData(textbook_id="textbook_1")
        assert graph.nodes == []
        assert graph.edges == []


class TestBuildGraphRequest:
    """Test BuildGraphRequest model."""

    def test_build_graph_request_creation(self):
        """Create a BuildGraphRequest."""
        req = BuildGraphRequest(textbook_id="textbook_1")
        assert req.textbook_id == "textbook_1"

    def test_build_graph_request_required(self):
        """BuildGraphRequest requires textbook_id."""
        with pytest.raises(ValidationError):
            BuildGraphRequest()  # type: ignore


class TestBuildGraphResponse:
    """Test BuildGraphResponse model."""

    def test_build_graph_response_creation(self):
        """Create a BuildGraphResponse."""
        resp = BuildGraphResponse(
            job_id="job_1",
            textbook_id="textbook_1",
            status="processing",
            message="Graph building started",
        )
        assert resp.job_id == "job_1"
        assert resp.textbook_id == "textbook_1"
        assert resp.status == "processing"


class TestGraphStatusResponse:
    """Test GraphStatusResponse model."""

    def test_graph_status_response_creation(self):
        """Create a GraphStatusResponse."""
        resp = GraphStatusResponse(
            job_id="job_1",
            textbook_id="textbook_1",
            status=GraphJobStatus.processing,
            progress_pct=50.0,
            total_chapters=10,
            processed_chapters=5,
        )
        assert resp.job_id == "job_1"
        assert resp.status == GraphJobStatus.processing
        assert resp.progress_pct == 50.0

    def test_graph_status_response_defaults(self):
        """GraphStatusResponse has sensible defaults."""
        resp = GraphStatusResponse(
            job_id="job_1",
            textbook_id="textbook_1",
            status=GraphJobStatus.pending,
        )
        assert resp.progress_pct == 0.0
        assert resp.total_chapters == 0
        assert resp.processed_chapters == 0
        assert resp.error is None


class TestConceptNodeDetail:
    """Test ConceptNodeDetail model."""

    def test_concept_node_detail_creation(self):
        """Create a ConceptNodeDetail."""
        node = ConceptNode(
            id="node_1",
            textbook_id="textbook_1",
            title="Theorem",
            node_type=NodeType.theorem,
            level=NodeLevel.section,
            created_at="2025-03-16T10:00:00Z",
        )
        edge_in = ConceptEdge(
            id="edge_1",
            textbook_id="textbook_1",
            source_node_id="node_0",
            target_node_id="node_1",
            relationship_type=RelationshipType.prerequisite_of,
            created_at="2025-03-16T10:00:00Z",
        )
        edge_out = ConceptEdge(
            id="edge_2",
            textbook_id="textbook_1",
            source_node_id="node_1",
            target_node_id="node_2",
            relationship_type=RelationshipType.proves,
            created_at="2025-03-16T10:00:00Z",
        )
        detail = ConceptNodeDetail(
            node=node,
            incoming_edges=[edge_in],
            outgoing_edges=[edge_out],
        )
        assert detail.node.id == "node_1"
        assert len(detail.incoming_edges) == 1
        assert len(detail.outgoing_edges) == 1

    def test_concept_node_detail_empty_edges(self):
        """ConceptNodeDetail defaults to empty edge lists."""
        node = ConceptNode(
            id="node_1",
            textbook_id="textbook_1",
            title="Theorem",
            node_type=NodeType.theorem,
            level=NodeLevel.section,
            created_at="2025-03-16T10:00:00Z",
        )
        detail = ConceptNodeDetail(node=node)
        assert detail.incoming_edges == []
        assert detail.outgoing_edges == []
