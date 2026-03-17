import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ReactFlow, ReactFlowProvider, MiniMap, Controls, Background,
  applyNodeChanges,
} from '@xyflow/react'
import type { Node, NodeChange, NodeMouseHandler, EdgeMouseHandler } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import '../styles/graph.css'
import { nodeTypes } from '../components/graph/nodeTypes'
import { useKnowledgeGraph } from '../hooks/useKnowledgeGraph'
import { PixelButton } from '../components/pixel/PixelButton'
import { GraphErrorBoundary } from '../components/graph/GraphErrorBoundary'
import { deleteGraph, buildGraph } from '../api/knowledgeGraph'
import { ConceptDetailPanel } from '../components/graph/ConceptDetailPanel'
import { DerivationPanel } from '../components/graph/DerivationPanel'

function GraphPageInner({ textbookId }: { textbookId: string }) {
  const navigate = useNavigate()
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const {
    nodes: layoutNodes,
    edges,
    isLoading,
    error,
    hasGraph,
    isGenerating,
    progressPct,
    processedChapters,
    totalChapters,
    selectedNodeId,
    setSelectedNodeId,
    reload,
  } = useKnowledgeGraph(textbookId)

  const [nodes, setNodes] = useState<Node[]>([])

  useEffect(() => {
    setNodes(layoutNodes)
  }, [layoutNodes])

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)),
    [],
  )

  const handleNodeClick: NodeMouseHandler = (_, node) => {
    setSelectedNodeId(node.id)
    setSelectedEdgeId(null)
  }

  const handleEdgeClick: EdgeMouseHandler = (_, edge) => {
    setSelectedEdgeId(edge.id)
    setSelectedNodeId(null)
  }

  const selectedEdge = selectedEdgeId ? (edges.find(e => e.id === selectedEdgeId) ?? null) : null

  const handleRegenerate = async () => {
    setIsRegenerating(true)
    try {
      await deleteGraph(textbookId)
      await buildGraph(textbookId)
      reload()
    } catch {
      setIsRegenerating(false)
    }
  }

  if (isLoading) {
    return (
      <div className="graph-page">
        <div className="graph-progress">
          <div>Loading knowledge graph...</div>
        </div>
      </div>
    )
  }

  if (isGenerating) {
    return (
      <div className="graph-page">
        <div className="graph-progress">
          <div>Generating knowledge graph...</div>
          <div>
            Chapter {processedChapters} of {totalChapters}
          </div>
          <div className="graph-progress__bar">
            <div className="graph-progress__fill" style={{ width: `${progressPct * 100}%` }} />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="graph-page">
        <div className="graph-page__header">
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← Back
          </PixelButton>
        </div>
        <div className="graph-progress">
          <div>Error: {error}</div>
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← Back to Bookshelf
          </PixelButton>
        </div>
      </div>
    )
  }

  if (!hasGraph) {
    return (
      <div className="graph-page">
        <div className="graph-page__header">
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← Back
          </PixelButton>
        </div>
        <div className="graph-progress">
          <div>No knowledge graph generated yet.</div>
          <PixelButton
            variant="primary"
            disabled={isRegenerating}
            onClick={handleRegenerate}
          >
            {isRegenerating ? 'Generating...' : 'Generate Now'}
          </PixelButton>
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← Back to Bookshelf
          </PixelButton>
        </div>
      </div>
    )
  }

  return (
    <div className="graph-page">
      <div className="graph-page__header">
        <PixelButton variant="secondary" onClick={() => navigate('/')}>
          ← Back
        </PixelButton>
        <span>Knowledge Graph</span>
        <PixelButton
          variant="primary"
          disabled={isRegenerating || isGenerating}
          onClick={handleRegenerate}
        >
          {isRegenerating ? 'Regenerating...' : 'Regenerate'}
        </PixelButton>
      </div>
      <GraphErrorBoundary fallback={
        <div className="graph-progress">
          <div>Graph rendering failed.</div>
          <PixelButton variant="secondary" onClick={() => navigate('/')}>
            ← Back to Bookshelf
          </PixelButton>
          <PixelButton variant="primary" onClick={handleRegenerate}>
            {isRegenerating ? 'Regenerating...' : 'Regenerate'}
          </PixelButton>
        </div>
      }>
        <div className="graph-page__canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            nodesConnectable={false}
            onlyRenderVisibleElements={true}
            fitView
            minZoom={0.1}
            maxZoom={2}
          >
            <MiniMap />
            <Controls />
            <Background />
          </ReactFlow>
          <ConceptDetailPanel
            textbookId={textbookId}
            nodeId={selectedNodeId}
            nodes={nodes}
            onClose={() => setSelectedNodeId(null)}
            onNavigateToNode={(nodeId) => {
              setSelectedNodeId(nodeId)
              setSelectedEdgeId(null)
            }}
          />
          <DerivationPanel
            edge={selectedEdge}
            nodes={nodes}
            onClose={() => setSelectedEdgeId(null)}
          />
        </div>
      </GraphErrorBoundary>
    </div>
  )
}

export default function GraphPage() {
  const { textbookId } = useParams<{ textbookId: string }>()
  if (!textbookId) return <div>Invalid textbook ID</div>
  return (
    <ReactFlowProvider>
      <GraphPageInner textbookId={textbookId} />
    </ReactFlowProvider>
  )
}
