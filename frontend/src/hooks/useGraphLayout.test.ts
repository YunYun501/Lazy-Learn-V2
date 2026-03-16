import { describe, it, expect } from 'vitest'
import { computeLayout } from './useGraphLayout'
import type { Node, Edge } from '@xyflow/react'

function makeNode(id: string, type = 'concept'): Node {
  return { id, type, position: { x: 0, y: 0 }, data: {} }
}

function makeEdge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target }
}

describe('computeLayout', () => {
  it('test_compute_layout_assigns_positions', () => {
    const nodes = [makeNode('A'), makeNode('B'), makeNode('C')]
    const edges = [makeEdge('A', 'B'), makeEdge('B', 'C')]

    const { nodes: layoutNodes } = computeLayout(nodes, edges)

    expect(layoutNodes).toHaveLength(3)
    layoutNodes.forEach((node) => {
      expect(typeof node.position.x).toBe('number')
      expect(typeof node.position.y).toBe('number')
      expect(Number.isNaN(node.position.x)).toBe(false)
      expect(Number.isNaN(node.position.y)).toBe(false)
    })

    const positions = layoutNodes.map((n) => `${n.position.x},${n.position.y}`)
    const uniquePositions = new Set(positions)
    expect(uniquePositions.size).toBeGreaterThan(1)
  })

  it('test_compute_layout_top_to_bottom_order', () => {
    const nodes = [makeNode('A'), makeNode('B'), makeNode('C')]
    const edges = [makeEdge('A', 'B'), makeEdge('B', 'C')]

    const { nodes: layoutNodes } = computeLayout(nodes, edges)

    const nodeMap = new Map(layoutNodes.map((n) => [n.id, n]))
    const posA = nodeMap.get('A')!.position.y
    const posB = nodeMap.get('B')!.position.y
    const posC = nodeMap.get('C')!.position.y

    expect(posA).toBeLessThan(posB)
    expect(posB).toBeLessThan(posC)
  })

  it('test_compute_layout_empty_returns_empty', () => {
    const { nodes, edges } = computeLayout([], [])

    expect(nodes).toEqual([])
    expect(edges).toEqual([])
  })

  it('test_compute_layout_respects_node_types', () => {
    const nodes = [
      makeNode('chapter1', 'chapter'),
      makeNode('concept1', 'concept'),
      makeNode('eq1', 'equation'),
    ]
    const edges: Edge[] = []

    const { nodes: layoutNodes } = computeLayout(nodes, edges)

    expect(layoutNodes).toHaveLength(3)
    layoutNodes.forEach((node) => {
      expect(typeof node.position.x).toBe('number')
      expect(typeof node.position.y).toBe('number')
    })

    expect(layoutNodes[0].type).toBe('chapter')
    expect(layoutNodes[1].type).toBe('concept')
    expect(layoutNodes[2].type).toBe('equation')
  })
})
