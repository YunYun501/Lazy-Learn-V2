import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import type { Node } from '@xyflow/react'
import { useExpandCollapse } from './useExpandCollapse'

type NodeLevel = 'chapter' | 'section' | 'subsection' | 'equation'

function makeNode(options: {
  id: string
  type: string
  level: NodeLevel
  sourceChapterId?: string
  sourceSectionId?: string
}): Node {
  const { id, type, level, sourceChapterId, sourceSectionId } = options
  return {
    id,
    type,
    position: { x: 0, y: 0 },
    data: { concept: { id, level, sourceChapterId, sourceSectionId } },
  }
}

describe('useExpandCollapse', () => {
  it('chapter toggle shows and hides section children', () => {
    const { result } = renderHook(() => useExpandCollapse())
    const nodes = [
      makeNode({ id: 'ch1', type: 'chapter', level: 'chapter' }),
      makeNode({ id: 'sec1', type: 'concept', level: 'section', sourceChapterId: 'ch1' }),
    ]

    const collapsed = result.current.applyVisibility(nodes, [])
    expect(collapsed.nodes.find((n) => n.id === 'ch1')?.hidden).toBe(false)
    expect(collapsed.nodes.find((n) => n.id === 'sec1')?.hidden).toBe(true)

    act(() => result.current.toggleChapter('ch1'))
    const expanded = result.current.applyVisibility(nodes, [])
    expect(expanded.nodes.find((n) => n.id === 'sec1')?.hidden).toBe(false)
  })

  it('section toggle shows and hides subsection and equation children', () => {
    const { result } = renderHook(() => useExpandCollapse())
    act(() => result.current.toggleChapter('ch1'))
    const nodes = [
      makeNode({ id: 'ch1', type: 'chapter', level: 'chapter' }),
      makeNode({ id: 'sec1', type: 'concept', level: 'section', sourceChapterId: 'ch1' }),
      makeNode({
        id: 'sub1',
        type: 'concept',
        level: 'subsection',
        sourceChapterId: 'ch1',
        sourceSectionId: 'sec1',
      }),
      makeNode({
        id: 'eq1',
        type: 'equation',
        level: 'equation',
        sourceChapterId: 'ch1',
        sourceSectionId: 'sec1',
      }),
    ]

    const chapterOnly = result.current.applyVisibility(nodes, [])
    expect(chapterOnly.nodes.find((n) => n.id === 'sec1')?.hidden).toBe(false)
    expect(chapterOnly.nodes.find((n) => n.id === 'sub1')?.hidden).toBe(true)
    expect(chapterOnly.nodes.find((n) => n.id === 'eq1')?.hidden).toBe(true)

    act(() => result.current.toggleSection('sec1'))
    const sectionExpanded = result.current.applyVisibility(nodes, [])
    expect(sectionExpanded.nodes.find((n) => n.id === 'sub1')?.hidden).toBe(false)
    expect(sectionExpanded.nodes.find((n) => n.id === 'eq1')?.hidden).toBe(false)
  })

  it('collapsing a chapter hides all descendants', () => {
    const { result } = renderHook(() => useExpandCollapse())
    act(() => result.current.toggleChapter('ch1'))
    act(() => result.current.toggleSection('sec1'))
    const nodes = [
      makeNode({ id: 'ch1', type: 'chapter', level: 'chapter' }),
      makeNode({ id: 'sec1', type: 'concept', level: 'section', sourceChapterId: 'ch1' }),
      makeNode({
        id: 'sub1',
        type: 'concept',
        level: 'subsection',
        sourceChapterId: 'ch1',
        sourceSectionId: 'sec1',
      }),
      makeNode({
        id: 'eq1',
        type: 'equation',
        level: 'equation',
        sourceChapterId: 'ch1',
        sourceSectionId: 'sec1',
      }),
    ]

    act(() => result.current.toggleChapter('ch1'))
    const collapsed = result.current.applyVisibility(nodes, [])
    expect(collapsed.nodes.find((n) => n.id === 'sec1')?.hidden).toBe(true)
    expect(collapsed.nodes.find((n) => n.id === 'sub1')?.hidden).toBe(true)
    expect(collapsed.nodes.find((n) => n.id === 'eq1')?.hidden).toBe(true)
  })

  it('section expansion resets when chapter collapses', () => {
    const { result } = renderHook(() => useExpandCollapse())
    const nodes = [
      makeNode({ id: 'ch1', type: 'chapter', level: 'chapter' }),
      makeNode({ id: 'sec1', type: 'concept', level: 'section', sourceChapterId: 'ch1' }),
      makeNode({
        id: 'sub1',
        type: 'concept',
        level: 'subsection',
        sourceChapterId: 'ch1',
        sourceSectionId: 'sec1',
      }),
    ]
    act(() => result.current.toggleChapter('ch1'))
    act(() => result.current.toggleSection('sec1'))
    result.current.applyVisibility(nodes, [])
    act(() => result.current.toggleChapter('ch1'))

    expect(result.current.isSectionExpanded('sec1')).toBe(false)

    act(() => result.current.toggleChapter('ch1'))
    const afterReset = result.current.applyVisibility(nodes, [])
    expect(afterReset.nodes.find((n) => n.id === 'sub1')?.hidden).toBe(true)
  })
})
