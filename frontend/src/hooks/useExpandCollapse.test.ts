import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useExpandCollapse } from './useExpandCollapse'
import type { Node, Edge } from '@xyflow/react'

function makeNode(id: string, type: string, sourceChapterId?: string): Node {
  return {
    id,
    type,
    position: { x: 0, y: 0 },
    data: { concept: { sourceChapterId } },
  }
}

function makeEdge(source: string, target: string): Edge {
  return { id: `${source}-${target}`, source, target }
}

describe('useExpandCollapse', () => {
  it('initially no chapters are expanded', () => {
    const { result } = renderHook(() => useExpandCollapse())
    expect(result.current.expandedChapters.size).toBe(0)
  })

  it('toggleChapter expands a chapter', () => {
    const { result } = renderHook(() => useExpandCollapse())
    act(() => result.current.toggleChapter('ch1'))
    expect(result.current.expandedChapters.has('ch1')).toBe(true)
  })

  it('toggleChapter collapses an already-expanded chapter', () => {
    const { result } = renderHook(() => useExpandCollapse())
    act(() => result.current.toggleChapter('ch1'))
    act(() => result.current.toggleChapter('ch1'))
    expect(result.current.expandedChapters.has('ch1')).toBe(false)
  })

  it('applyVisibility hides non-chapter nodes when chapter collapsed', () => {
    const { result } = renderHook(() => useExpandCollapse())
    const nodes = [makeNode('ch1', 'chapter'), makeNode('sec1', 'concept', 'ch1')]
    const { nodes: visibleNodes } = result.current.applyVisibility(nodes, [])
    expect(visibleNodes.find((n) => n.id === 'ch1')?.hidden).toBe(false)
    expect(visibleNodes.find((n) => n.id === 'sec1')?.hidden).toBe(true)
  })

  it('applyVisibility shows section nodes when chapter expanded', () => {
    const { result } = renderHook(() => useExpandCollapse())
    act(() => result.current.toggleChapter('ch1'))
    const nodes = [makeNode('ch1', 'chapter'), makeNode('sec1', 'concept', 'ch1')]
    const { nodes: visibleNodes } = result.current.applyVisibility(nodes, [])
    expect(visibleNodes.find((n) => n.id === 'sec1')?.hidden).toBe(false)
  })

  it('applyVisibility hides edges when connected nodes are hidden', () => {
    const { result } = renderHook(() => useExpandCollapse())
    const nodes = [makeNode('ch1', 'chapter'), makeNode('sec1', 'concept', 'ch1')]
    const edges = [makeEdge('ch1', 'sec1')]
    const { edges: visibleEdges } = result.current.applyVisibility(nodes, edges)
    expect(visibleEdges[0].hidden).toBe(true)
  })
})
