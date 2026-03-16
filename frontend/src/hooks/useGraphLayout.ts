import { useMemo } from 'react'
import type { Node, Edge } from '@xyflow/react'
import dagre from '@dagrejs/dagre'

const NODE_DIMENSIONS: Record<string, { width: number; height: number }> = {
  chapter: { width: 200, height: 80 },
  concept: { width: 180, height: 60 },
  equation: { width: 160, height: 50 },
  default: { width: 180, height: 60 },
}

export function computeLayout(nodes: Node[], edges: Edge[]): { nodes: Node[]; edges: Edge[] } {
  if (nodes.length === 0) return { nodes: [], edges: [] }

  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120 })

  nodes.forEach((node) => {
    const type = node.type ?? 'default'
    const dims = NODE_DIMENSIONS[type] ?? NODE_DIMENSIONS.default
    g.setNode(node.id, { width: dims.width, height: dims.height })
  })

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  const layoutNodes = nodes.map((node) => {
    const pos = g.node(node.id)
    const type = node.type ?? 'default'
    const dims = NODE_DIMENSIONS[type] ?? NODE_DIMENSIONS.default
    return {
      ...node,
      position: {
        x: pos.x - dims.width / 2,
        y: pos.y - dims.height / 2,
      },
    }
  })

  return { nodes: layoutNodes, edges }
}

export function useGraphLayout(nodes: Node[], edges: Edge[]) {
  return useMemo(() => computeLayout(nodes, edges), [nodes, edges])
}
