// Union types (matching backend enums)
export type NodeType =
  | 'theorem' | 'definition' | 'equation' | 'lemma' | 'corollary' | 'axiom' | 'proof' | 'identity' | 'formula'
  | 'law' | 'principle' | 'theory' | 'hypothesis' | 'observation' | 'constant' | 'property'
  | 'method' | 'technique' | 'algorithm' | 'procedure' | 'criterion' | 'model' | 'approximation' | 'rule' | 'condition' | 'relation'
  | 'concept' | 'result' | 'example'
export type NodeLevel = 'chapter' | 'section' | 'subsection'
export type RelationshipType =
  | 'derives_from'
  | 'proves'
  | 'prerequisite_of'
  | 'uses'
  | 'generalizes'
  | 'specializes'
  | 'contradicts'
  | 'defines'
  | 'equivalent_form'
  | 'variant_of'
  | 'contains'
export type GraphJobStatus = 'pending' | 'processing' | 'completed' | 'failed'

// Core data interfaces (camelCase — maps from backend snake_case)
export interface ConceptNode {
  id: string
  textbookId: string
  title: string
  description?: string
  nodeType: NodeType
  level: NodeLevel
  sourceChapterId?: string
  sourceSectionId?: string
  sourcePage?: number
  metadata?: Record<string, unknown>
  createdAt: string
}

export interface ConceptEdge {
  id: string
  textbookId: string
  sourceNodeId: string
  targetNodeId: string
  relationshipType: RelationshipType
  confidence: number
  reasoning?: string
  metadata?: Record<string, unknown>
  createdAt: string
}

export interface GraphData {
  textbookId: string
  nodes: ConceptNode[]
  edges: ConceptEdge[]
}

// API response types
export interface BuildGraphResponse {
  jobId: string
  textbookId: string
  status: string
  message: string
}

export interface GraphStatusResponse {
  jobId: string
  textbookId: string
  status: GraphJobStatus
  progressPct: number
  totalChapters: number
  processedChapters: number
  error?: string
}

export interface ConceptNodeDetail {
  node: ConceptNode
  incomingEdges: ConceptEdge[]
  outgoingEdges: ConceptEdge[]
}

// React Flow compatible types (for use with @xyflow/react)
export interface ConceptNodeData {
  concept: ConceptNode
  isExpanded?: boolean
  childCount?: number
}

// Type guard functions
const NODE_TYPES: NodeType[] = [
  'theorem', 'definition', 'equation', 'lemma', 'corollary', 'axiom', 'proof', 'identity', 'formula',
  'law', 'principle', 'theory', 'hypothesis', 'observation', 'constant', 'property',
  'method', 'technique', 'algorithm', 'procedure', 'criterion', 'model', 'approximation', 'rule', 'condition', 'relation',
  'concept', 'result', 'example',
]

export function isValidNodeType(value: string): value is NodeType {
  return NODE_TYPES.includes(value as NodeType)
}

const NODE_LEVELS: NodeLevel[] = [
  'chapter',
  'section',
  'subsection',
]

export function isValidNodeLevel(value: string): value is NodeLevel {
  return NODE_LEVELS.includes(value as NodeLevel)
}

const RELATIONSHIP_TYPES: RelationshipType[] = [
  'derives_from',
  'proves',
  'prerequisite_of',
  'uses',
  'generalizes',
  'specializes',
  'contradicts',
  'defines',
  'equivalent_form',
  'variant_of',
  'contains',
]

export function isValidRelationshipType(value: string): value is RelationshipType {
  return RELATIONSHIP_TYPES.includes(value as RelationshipType)
}
