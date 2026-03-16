import React from 'react'
import { Handle, Position } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { ConceptNodeData } from '../../types/knowledgeGraph'
import { InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'

type EquationFlowNode = Node<ConceptNodeData, 'equation'>

const EquationNode = React.memo(({ data, selected }: NodeProps<EquationFlowNode>) => {
  const latex = data.concept.metadata?.latex as string | undefined
  return (
    <div className={`graph-node graph-node--equation ${selected ? 'graph-node--selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      {latex ? (
        <InlineMath math={latex} />
      ) : (
        <div className="graph-node__title">{data.concept.title}</div>
      )}
      {data.concept.sourcePage !== undefined && (
        <div className="graph-node__source">p.{data.concept.sourcePage}</div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})
EquationNode.displayName = 'EquationNode'

export default EquationNode
