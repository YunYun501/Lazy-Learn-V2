import { useState, useEffect } from 'react'
import type { Node, Edge } from '@xyflow/react'
import { getGraphData, getGraphStatus, pollGraphStatus } from '../api/knowledgeGraph'
import type { GraphData, ConceptNode, ConceptEdge } from '../types/knowledgeGraph'
import { computeLayout } from './useGraphLayout'

interface UseKnowledgeGraphReturn {
  nodes: Node[]
  edges: Edge[]
  isLoading: boolean
  isGenerating: boolean
  progressPct: number
  processedChapters: number
  totalChapters: number
  error: string | null
  hasGraph: boolean
  selectedNodeId: string | null
  setSelectedNodeId: (id: string | null) => void
  reload: () => void
}

function mapNodeToFlow(concept: ConceptNode): Node {
   return {
     id: concept.id,
     type: concept.level === 'chapter' ? 'chapter' : 'concept',
     position: { x: 0, y: 0 }, // will be replaced by dagre layout
     data: { concept, isExpanded: false, childCount: 0 },
   }
 }

function mapEdgeToFlow(edge: ConceptEdge): Edge {
  return {
    id: edge.id,
    source: edge.sourceNodeId,
    target: edge.targetNodeId,
    label: edge.relationshipType.replace(/_/g, ' '),
    data: {
      relationshipType: edge.relationshipType,
      confidence: edge.confidence,
      reasoning: edge.reasoning,
      metadata: edge.metadata,
    },
  }
}

export function useKnowledgeGraph(textbookId: string): UseKnowledgeGraphReturn {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)
  const [progressPct, setProgressPct] = useState(0)
  const [processedChapters, setProcessedChapters] = useState(0)
  const [totalChapters, setTotalChapters] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setIsLoading(true)
      setError(null)
      try {
        // Check if a job is in progress
        const status = await getGraphStatus(textbookId).catch(() => null)
        if (status?.status === 'processing') {
          setIsGenerating(true)
          setProgressPct(status.progressPct)
          setProcessedChapters(status.processedChapters)
          setTotalChapters(status.totalChapters)
          pollGraphStatus(
            textbookId,
            2000,
            (pollStatus) => {
              if (!cancelled) {
                setProgressPct(pollStatus.progressPct)
                setProcessedChapters(pollStatus.processedChapters)
                setTotalChapters(pollStatus.totalChapters)
              }
            }
          ).then((finalStatus) => {
            if (!cancelled) {
              if (finalStatus.status === 'completed') {
                setReloadCount((c) => c + 1)
              } else if (finalStatus.status === 'failed') {
                setError(finalStatus.error ?? 'Graph generation failed')
                setIsGenerating(false)
              }
            }
          }).catch(() => {
            if (!cancelled) {
              setIsGenerating(false)
              setError('Failed to track graph generation progress')
            }
          })
        } else if (status?.status === 'completed' || !status) {
          const data = await getGraphData(textbookId).catch(() => null)
          if (!cancelled) {
            setGraphData(data)
            setIsGenerating(false)
          }
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [textbookId, reloadCount])

  const rawNodes = graphData?.nodes.map(mapNodeToFlow) ?? []
  const rawEdges = graphData?.edges.map(mapEdgeToFlow) ?? []
  const { nodes, edges } = computeLayout(rawNodes, rawEdges)

  return {
    nodes,
    edges,
    isLoading,
    isGenerating,
    progressPct,
    processedChapters,
    totalChapters,
    error,
    hasGraph: !!graphData && graphData.nodes.length > 0,
    selectedNodeId,
    setSelectedNodeId,
    reload: () => setReloadCount((c) => c + 1),
  }
}
