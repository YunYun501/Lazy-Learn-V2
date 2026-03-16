import React from 'react'
import { Handle, Position } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { ConceptNodeData, NodeType } from '../../types/knowledgeGraph'

const NODE_TYPE_CLASS: Record<NodeType, string> = {
  theorem: 'graph-node--theorem',
  definition: 'graph-node--definition',
  equation: 'graph-node--equation',
  lemma: 'graph-node--lemma',
  concept: 'graph-node--concept',
  example: 'graph-node--example',
}

type ConceptFlowNode = Node<ConceptNodeData, 'concept'>

const ConceptNode = React.memo(({ data, selected }: NodeProps<ConceptFlowNode>) => {
  const typeClass = NODE_TYPE_CLASS[data.concept.nodeType] ?? 'graph-node--concept'
  return (
    <div className={`graph-node ${typeClass} ${selected ? 'graph-node--selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="graph-node__title">{data.concept.title}</div>
      <div className="graph-node__badge">{data.concept.nodeType}</div>
      {data.concept.sourcePage !== undefined && (
        <div className="graph-node__source">p.{data.concept.sourcePage}</div>
      )}
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})
ConceptNode.displayName = 'ConceptNode'

export default ConceptNode
