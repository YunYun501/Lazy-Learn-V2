import React from 'react'
import { Handle, Position } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { ConceptNodeData } from '../../types/knowledgeGraph'
import { InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'

type EquationFlowNode = Node<ConceptNodeData, 'equation'>

const EquationNode = React.memo(({ data, selected }: NodeProps<EquationFlowNode>) => {
  const rawLatex = data.concept.metadata?.raw_latex as string | undefined
  const variables = data.concept.metadata?.variables as string[] | undefined
  const varCount = variables?.length ?? 0

  return (
    <div className={`graph-node graph-node--equation ${selected ? 'graph-node--selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      {rawLatex ? (
        <InlineMath
          math={rawLatex}
          renderError={() => (
            <div className="graph-node__title" style={{ fontSize: 7 }}>{rawLatex}</div>
          )}
        />
      ) : (
        <div className="graph-node__title">{data.concept.title}</div>
      )}
      <div className="graph-node__footer">
        {varCount > 0 && (
          <span className="graph-node__vars">{varCount} var{varCount !== 1 ? 's' : ''}</span>
        )}
        {data.concept.sourcePage !== undefined && (
          <span className="graph-node__source">p.{data.concept.sourcePage}</span>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})
EquationNode.displayName = 'EquationNode'

export default EquationNode
