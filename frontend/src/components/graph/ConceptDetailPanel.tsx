import { useEffect, useState } from 'react'
import { getNodeDetail } from '../../api/knowledgeGraph'
import type { ConceptNodeDetail } from '../../types/knowledgeGraph'

interface ConceptDetailPanelProps {
  textbookId: string
  nodeId: string | null
  onClose: () => void
}

export function ConceptDetailPanel({ textbookId, nodeId, onClose }: ConceptDetailPanelProps) {
  const [detail, setDetail] = useState<ConceptNodeDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!nodeId) { setDetail(null); return }
    setIsLoading(true)
    setError(null)
    getNodeDetail(textbookId, nodeId)
      .then(d => { setDetail(d); setIsLoading(false) })
      .catch(e => { setError((e as Error).message); setIsLoading(false) })
  }, [textbookId, nodeId])

  if (!nodeId) return null

  return (
    <div className="concept-detail-panel" data-testid="concept-detail-panel">
      <button className="concept-detail-panel__close" onClick={onClose} aria-label="Close">✕</button>
      {isLoading && <div>Loading...</div>}
      {error && <div className="concept-detail-panel__error">Error: {error}</div>}
      {detail && (
        <>
          <div className="concept-detail-panel__header">
            <h3 className="concept-detail-panel__title">{detail.node.title}</h3>
            <span className="concept-detail-panel__badge">{detail.node.nodeType}</span>
          </div>
          {detail.node.description && (
            <p className="concept-detail-panel__description">{detail.node.description}</p>
          )}
          {detail.node.sourcePage && (
            <div className="concept-detail-panel__source">
              Found in: Page {detail.node.sourcePage}
            </div>
          )}
          {detail.outgoingEdges.length > 0 && (
            <div className="concept-detail-panel__relations">
              <h4>Relationships</h4>
              <ul>
                {detail.outgoingEdges.map(edge => (
                  <li key={edge.id}>
                    <span className="edge-type">{edge.relationshipType.replace(/_/g, ' ')}</span>
                    {': '}
                    <span className="edge-target">{edge.targetNodeId}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {detail.incomingEdges.length > 0 && (
            <div className="concept-detail-panel__relations">
              <h4>Used by</h4>
              <ul>
                {detail.incomingEdges.map(edge => (
                  <li key={edge.id}>
                    <span className="edge-source">{edge.sourceNodeId}</span>
                    {' → '}
                    <span className="edge-type">{edge.relationshipType.replace(/_/g, ' ')}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
