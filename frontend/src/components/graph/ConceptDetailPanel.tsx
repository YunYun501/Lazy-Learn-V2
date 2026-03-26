import { useEffect, useState, useMemo } from 'react'
import 'katex/dist/katex.min.css'
import { BlockMath } from 'react-katex'
import type { Node } from '@xyflow/react'
import { getNodeDetail } from '../../api/knowledgeGraph'
import type { ConceptNodeDetail } from '../../types/knowledgeGraph'

interface EquationComponent {
  symbol: string
  name: string
  type: 'calculated' | 'constant'
  description: string
  latex?: string | null
  page_reference?: string | null
  linked_node_id?: string | null
}

interface ConceptDetailPanelProps {
  textbookId: string
  nodeId: string | null
  nodes: Node[]
  onClose: () => void
  onNavigateToNode?: (nodeId: string) => void
}

function EquationDisplay({ latex }: { latex: string }) {
  try {
    return <BlockMath math={latex} />
  } catch {
    return <code>{latex}</code>
  }
}

export function ConceptDetailPanel({ textbookId, nodeId, nodes, onClose, onNavigateToNode }: ConceptDetailPanelProps) {
  const [detail, setDetail] = useState<ConceptNodeDetail | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const titleById = useMemo(() => {
    const map = new Map<string, string>()
    for (const n of nodes) {
      const concept = (n.data as Record<string, unknown>)?.concept as { title?: string } | undefined
      if (concept?.title) map.set(n.id, concept.title)
    }
    return map
  }, [nodes])

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
          {detail.node.metadata?.section_path && (
            <div className="concept-detail-panel__source">
              Section: {String(detail.node.metadata.section_path)}
            </div>
          )}
           {detail.node.metadata?.defining_equation && (
             <div className="concept-detail-panel__relations">
               <h4>Defining Equation</h4>
               <div className="concept-detail-panel__equation">
                 <BlockMath math={String(detail.node.metadata.defining_equation)} />
               </div>
             </div>
           )}
          {Array.isArray(detail.node.metadata?.equation_components) &&
            (detail.node.metadata.equation_components as EquationComponent[]).length > 0 && (
            <div className="concept-detail-panel__relations">
              <h4>Equation Breakdown</h4>
              <ul className="concept-detail-panel__breakdown">
                {(detail.node.metadata.equation_components as EquationComponent[]).map((comp) => (
                  <li
                    key={comp.symbol}
                    className={`concept-detail-panel__variable concept-detail-panel__variable--${comp.type}`}
                    onClick={
                      comp.type === 'calculated' && comp.linked_node_id && onNavigateToNode
                        ? () => onNavigateToNode(comp.linked_node_id!)
                        : undefined
                    }
                    style={{ cursor: comp.type === 'calculated' && comp.linked_node_id ? 'pointer' : 'default' }}
                  >
                    <span className="concept-detail-panel__variable-symbol">{comp.symbol}</span>
                    {' = '}
                    <span className="concept-detail-panel__variable-name">{comp.name}</span>
                    <div className="concept-detail-panel__variable-desc">{comp.description}</div>
                    {comp.type === 'calculated' && comp.latex && (
                      <div className="concept-detail-panel__equation">
                        <EquationDisplay latex={comp.latex} />
                      </div>
                    )}
                    {comp.type === 'constant' && comp.page_reference && (
                      <div className="concept-detail-panel__page-ref">📌 {comp.page_reference}</div>
                    )}
                  </li>
                ))}
              </ul>
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
                     <span className="edge-target">{titleById.get(edge.targetNodeId) ?? edge.targetNodeId}</span>
                     {edge.reasoning && (
                       <div className="edge-reasoning">{edge.reasoning}</div>
                     )}
                     {edge.metadata?.derivation_steps && Array.isArray(edge.metadata.derivation_steps) && (edge.metadata.derivation_steps as string[]).length > 0 && (
                       <div className="derivation-chain">
                         {edge.metadata.transformation_context && (
                           <div className="derivation-chain__context">
                             {(edge.metadata.transformation_context as { setting?: string }).setting && (
                               <div className="derivation-chain__setting">
                                 <strong>Context:</strong> {String((edge.metadata.transformation_context as { setting?: string }).setting)}
                               </div>
                             )}
                             {Array.isArray((edge.metadata.transformation_context as { assumptions?: string[] }).assumptions) &&
                               ((edge.metadata.transformation_context as { assumptions: string[] }).assumptions).length > 0 && (
                               <div className="derivation-chain__assumptions">
                                 <strong>Assumptions:</strong>
                                 <ul>
                                   {((edge.metadata.transformation_context as { assumptions: string[] }).assumptions).map((a, i) => (
                                     <li key={i}>{a}</li>
                                   ))}
                                 </ul>
                               </div>
                             )}
                             {Array.isArray((edge.metadata.transformation_context as { substitutions?: { from: string; to: string; reason: string }[] }).substitutions) &&
                               ((edge.metadata.transformation_context as { substitutions: { from: string; to: string; reason: string }[] }).substitutions).length > 0 && (
                               <div className="derivation-chain__substitutions">
                                 <strong>Substitutions:</strong>
                                 <ul>
                                   {((edge.metadata.transformation_context as { substitutions: { from: string; to: string; reason: string }[] }).substitutions).map((s, i) => (
                                     <li key={i}>
                                       <EquationDisplay latex={s.from} /> → <EquationDisplay latex={s.to} />
                                       {s.reason && <span className="derivation-chain__reason"> ({s.reason})</span>}
                                     </li>
                                   ))}
                                 </ul>
                               </div>
                             )}
                           </div>
                         )}
                         <div className="derivation-chain__steps">
                           <strong>Derivation Steps:</strong>
                           {(edge.metadata.derivation_steps as string[]).map((step, i) => (
                             <div key={i} className="derivation-chain__step">
                               <span className="derivation-chain__step-num">{i + 1}</span>
                               <div className="derivation-chain__step-math">
                                 <EquationDisplay latex={step} />
                               </div>
                             </div>
                           ))}
                         </div>
                       </div>
                     )}
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
                    <span className="edge-source">{titleById.get(edge.sourceNodeId) ?? edge.sourceNodeId}</span>
                    {' → '}
                    <span className="edge-type">{edge.relationshipType.replace(/_/g, ' ')}</span>
                    {edge.reasoning && (
                      <div className="edge-reasoning">{edge.reasoning}</div>
                    )}
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
