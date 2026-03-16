from enum import Enum
from pydantic import BaseModel
from typing import Optional


class NodeType(str, Enum):
    """Type of concept node in the knowledge graph.

    Comprehensive list covering common STEM textbook entities.
    The builder clamps any unrecognised LLM output to 'concept'.
    """

    # --- core mathematical ---
    theorem = "theorem"
    definition = "definition"
    equation = "equation"
    lemma = "lemma"
    corollary = "corollary"
    axiom = "axiom"
    proof = "proof"
    identity = "identity"
    formula = "formula"

    # --- scientific / physical ---
    law = "law"
    principle = "principle"
    theory = "theory"
    hypothesis = "hypothesis"
    observation = "observation"
    constant = "constant"
    property = "property"

    # --- engineering / applied ---
    method = "method"
    technique = "technique"
    algorithm = "algorithm"
    procedure = "procedure"
    criterion = "criterion"
    model = "model"
    approximation = "approximation"
    rule = "rule"
    condition = "condition"
    relation = "relation"

    # --- general ---
    concept = "concept"
    result = "result"
    example = "example"


class RelationshipType(str, Enum):
    """Type of relationship between concept nodes."""

    derives_from = "derives_from"
    proves = "proves"
    prerequisite_of = "prerequisite_of"
    uses = "uses"
    generalizes = "generalizes"
    specializes = "specializes"
    contradicts = "contradicts"
    defines = "defines"
    equivalent_form = "equivalent_form"
    variant_of = "variant_of"
    contains = "contains"


class GraphJobStatus(str, Enum):
    """Status of a graph building job."""

    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class NodeLevel(str, Enum):
    """Hierarchical level of a concept node."""

    chapter = "chapter"
    section = "section"
    subsection = "subsection"


class ConceptNode(BaseModel):
    """A node representing a concept in the knowledge graph."""

    id: str
    textbook_id: str
    title: str
    description: Optional[str] = None
    node_type: NodeType
    level: NodeLevel
    source_chapter_id: Optional[str] = None
    source_section_id: Optional[str] = None
    source_page: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: str


class ConceptEdge(BaseModel):
    """An edge representing a relationship between two concept nodes."""

    id: str
    textbook_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    reasoning: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str


class GraphData(BaseModel):
    """Complete knowledge graph data for a textbook."""

    textbook_id: str
    nodes: list[ConceptNode] = []
    edges: list[ConceptEdge] = []


class BuildGraphRequest(BaseModel):
    """Request to build a knowledge graph for a textbook."""

    textbook_id: str


class BuildGraphResponse(BaseModel):
    """Response from a graph building request."""

    job_id: str
    textbook_id: str
    status: str
    message: str


class GraphStatusResponse(BaseModel):
    """Response with current status of a graph building job."""

    job_id: str
    textbook_id: str
    status: GraphJobStatus
    progress_pct: float = 0.0
    total_chapters: int = 0
    processed_chapters: int = 0
    error: Optional[str] = None


class ConceptNodeDetail(BaseModel):
    """Detailed view of a concept node with its incoming and outgoing edges."""

    node: ConceptNode
    incoming_edges: list[ConceptEdge] = []
    outgoing_edges: list[ConceptEdge] = []
