import { API_BASE } from './config'
import { logger } from '../services/logger'
import type {
  BuildGraphResponse,
  GraphStatusResponse,
  GraphData,
  ConceptNodeDetail,
  ConceptNode,
  ConceptEdge,
} from '../types/knowledgeGraph'

function mapNode(raw: Record<string, unknown>): ConceptNode {
  return {
    id: raw.id as string,
    textbookId: raw.textbook_id as string,
    title: raw.title as string,
    description: raw.description as string | undefined,
    nodeType: raw.node_type as ConceptNode['nodeType'],
    level: raw.level as ConceptNode['level'],
    sourceChapterId: raw.source_chapter_id as string | undefined,
    sourceSectionId: raw.source_section_id as string | undefined,
    sourcePage: raw.source_page as number | undefined,
    metadata: raw.metadata as Record<string, unknown> | undefined,
    createdAt: raw.created_at as string,
  }
}

function mapEdge(raw: Record<string, unknown>): ConceptEdge {
  return {
    id: raw.id as string,
    textbookId: raw.textbook_id as string,
    sourceNodeId: raw.source_node_id as string,
    targetNodeId: raw.target_node_id as string,
    relationshipType: raw.relationship_type as ConceptEdge['relationshipType'],
    confidence: raw.confidence as number,
    reasoning: raw.reasoning as string | undefined,
    metadata: raw.metadata as Record<string, unknown> | undefined,
    createdAt: raw.created_at as string,
  }
}

export async function buildGraph(textbookId: string): Promise<BuildGraphResponse> {
  const url = `${API_BASE}/knowledge-graph/${textbookId}/build`
  logger.info(`Building graph for textbook ${textbookId}`, { component: 'knowledgeGraph' })
  const res = await fetch(url, { method: 'POST' })
  if (!res.ok) {
    logger.error(`Build graph failed: ${res.status}`, { component: 'knowledgeGraph', context: textbookId })
    throw new Error(`Failed to build graph: ${res.status}`)
  }
  const raw = (await res.json()) as Record<string, unknown>
  return {
    jobId: raw.job_id as string,
    textbookId: raw.textbook_id as string,
    status: raw.status as string,
    message: raw.message as string,
  }
}

export async function getGraphStatus(textbookId: string): Promise<GraphStatusResponse> {
  const url = `${API_BASE}/knowledge-graph/${textbookId}/status`
  const res = await fetch(url, { method: 'GET' })
  if (!res.ok) throw new Error(`Failed to get graph status: ${res.status}`)
  const raw = (await res.json()) as Record<string, unknown>
  return {
    jobId: raw.job_id as string,
    textbookId: raw.textbook_id as string,
    status: raw.status as GraphStatusResponse['status'],
    progressPct: raw.progress_pct as number,
    totalChapters: raw.total_chapters as number,
    processedChapters: raw.processed_chapters as number,
    error: raw.error as string | undefined,
  }
}

export async function getGraphData(textbookId: string): Promise<GraphData> {
  const url = `${API_BASE}/knowledge-graph/${textbookId}/graph`
  const res = await fetch(url, { method: 'GET' })
  if (!res.ok) {
    logger.error(`Get graph data failed: ${res.status}`, { component: 'knowledgeGraph', context: textbookId })
    throw new Error(`Failed to get graph data: ${res.status}`)
  }
  const raw = (await res.json()) as Record<string, unknown>
  return {
    textbookId: raw.textbook_id as string,
    nodes: ((raw.nodes as Record<string, unknown>[]) || []).map(mapNode),
    edges: ((raw.edges as Record<string, unknown>[]) || []).map(mapEdge),
  }
}

export async function getNodeDetail(
  textbookId: string,
  nodeId: string
): Promise<ConceptNodeDetail> {
  const url = `${API_BASE}/knowledge-graph/${textbookId}/node/${nodeId}`
  const res = await fetch(url, { method: 'GET' })
  if (!res.ok) throw new Error(`Failed to get node detail: ${res.status}`)
  const raw = (await res.json()) as Record<string, unknown>
  return {
    node: mapNode(raw.node as Record<string, unknown>),
    incomingEdges: ((raw.incoming_edges as Record<string, unknown>[]) || []).map(mapEdge),
    outgoingEdges: ((raw.outgoing_edges as Record<string, unknown>[]) || []).map(mapEdge),
  }
}

export async function deleteGraph(textbookId: string): Promise<void> {
  const url = `${API_BASE}/knowledge-graph/${textbookId}`
  const res = await fetch(url, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Failed to delete graph: ${res.status}`)
}

export async function pollGraphStatus(
  textbookId: string,
  intervalMs: number,
  onProgress: (status: GraphStatusResponse) => void
): Promise<GraphStatusResponse> {
  let status = await getGraphStatus(textbookId)
  onProgress(status)

  while (status.status !== 'completed' && status.status !== 'failed') {
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
    status = await getGraphStatus(textbookId)
    onProgress(status)
  }

  return status
}
