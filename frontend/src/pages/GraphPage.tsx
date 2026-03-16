import { useParams, useNavigate } from 'react-router-dom'
import { ReactFlow, ReactFlowProvider, MiniMap, Controls, Background } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import '../styles/graph.css'
import { nodeTypes } from '../components/graph/nodeTypes'
import { useKnowledgeGraph } from '../hooks/useKnowledgeGraph'
import { PixelButton } from '../components/pixel/PixelButton'
import { GraphErrorBoundary } from '../components/graph/GraphErrorBoundary'
import type { NodeMouseHandler } from '@xyflow/react'

function GraphPageInner({ textbookId }: { textbookId: string }) {
  const navigate = useNavigate()
  const {
    nodes,
    edges,
    isLoading,
    error,
    hasGraph,
    isGenerating,
    progressPct,
    processedChapters,
    totalChapters,
    setSelectedNodeId,
  } = useKnowledgeGraph(textbookId)

  const handleNodeClick: NodeMouseHandler = (_, node) => {
    setSelectedNodeId(node.id)
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
          <div>Go back and click &quot;Generate Relationship&quot; to build one.</div>
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
      </div>
      <GraphErrorBoundary>
        <div className="graph-page__canvas">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={handleNodeClick}
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
