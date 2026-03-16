import React from 'react'
import { Handle, Position } from '@xyflow/react'
import type { Node, NodeProps } from '@xyflow/react'
import type { ConceptNodeData } from '../../types/knowledgeGraph'

type ChapterData = {
  concept: ConceptNodeData['concept']
  isExpanded?: boolean
  childCount?: number
}
type ChapterFlowNode = Node<ChapterData, 'chapter'>

const ChapterNode = React.memo(({ data, selected }: NodeProps<ChapterFlowNode>) => {
  return (
    <div className={`graph-node graph-node--chapter ${selected ? 'graph-node--selected' : ''}`}>
      <Handle type="target" position={Position.Top} />
      <div className="graph-node__title">{data.concept.title}</div>
      <div className="graph-node__meta">
        <span className="graph-node__type">Chapter</span>
        {data.childCount !== undefined && (
          <span className="graph-node__count">{data.childCount} concepts</span>
        )}
        <span className="graph-node__expand">{data.isExpanded ? '▼' : '▶'}</span>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  )
})
ChapterNode.displayName = 'ChapterNode'

export default ChapterNode
