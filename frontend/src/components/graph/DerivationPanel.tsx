import React from 'react'
import 'katex/dist/katex.min.css'
import { BlockMath } from 'react-katex'
import type { Edge, Node } from '@xyflow/react'

interface EdgeMetadata {
  derivation_steps?: string[]
  [key: string]: unknown
}

interface ConceptEdgeData {
  relationshipType?: string
  confidence?: number
  reasoning?: string
  metadata?: EdgeMetadata
}

interface ConceptNodeData {
  concept?: {
    title?: string
    [key: string]: unknown
  }
  [key: string]: unknown
}

interface DerivationPanelProps {
  edge: Edge | null
  nodes: Node[]
  onClose: () => void
}

export const DerivationPanel = React.memo(function DerivationPanel({
  edge,
  nodes,
  onClose,
}: DerivationPanelProps) {
  if (!edge) return null

  const sourceNode = nodes.find(n => n.id === edge.source)
  const targetNode = nodes.find(n => n.id === edge.target)

  const sourceData = (sourceNode?.data ?? {}) as ConceptNodeData
  const targetData = (targetNode?.data ?? {}) as ConceptNodeData

  const sourceTitle = sourceData.concept?.title ?? edge.source
  const targetTitle = targetData.concept?.title ?? edge.target

  const edgeData = (edge.data ?? {}) as ConceptEdgeData
  const relationshipType = edgeData.relationshipType ?? 'unknown'
  const reasoning = edgeData.reasoning ?? ''
  const derivationSteps: string[] = edgeData.metadata?.derivation_steps ?? []

  return (
    <div className="derivation-panel" data-testid="derivation-panel">
      <button
        className="derivation-panel__close"
        onClick={onClose}
        aria-label="Close"
      >
        ✕
      </button>

      <div className="derivation-panel__header">
        <h3 className="derivation-panel__title">Derivation</h3>
        <span className="derivation-panel__badge">
          {relationshipType.replace(/_/g, ' ')}
        </span>
      </div>

      <div className="derivation-panel__flow">
        <span className="derivation-panel__node-name">{sourceTitle}</span>
        <span className="derivation-panel__arrow">→</span>
        <span className="derivation-panel__node-name">{targetTitle}</span>
      </div>

      {reasoning && (
        <p className="derivation-panel__reasoning">{reasoning}</p>
      )}

      {derivationSteps.length > 0 && (
        <div className="derivation-panel__steps">
          <h4 className="derivation-panel__steps-heading">Derivation Steps</h4>
          {derivationSteps.map((step, i) => (
            <div key={i} className="derivation-panel__step">
              <span className="derivation-panel__step-number">{i + 1}</span>
              <div className="derivation-panel__step-math">
                <BlockMath math={step} />
              </div>
            </div>
          ))}
        </div>
      )}

      {derivationSteps.length === 0 && !reasoning && (
        <p className="derivation-panel__empty">No derivation details available.</p>
      )}
    </div>
  )
})
