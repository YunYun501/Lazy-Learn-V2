import { describe, it, expect } from 'vitest'
import { nodeTypes } from './nodeTypes'
import ChapterNode from './ChapterNode'
import ConceptNode from './ConceptNode'

describe('nodeTypes', () => {
  it('has chapter key', () => {
    expect(nodeTypes).toHaveProperty('chapter')
  })

  it('has concept key', () => {
    expect(nodeTypes).toHaveProperty('concept')
  })

  it('maps chapter to ChapterNode component', () => {
    expect(nodeTypes.chapter).toBe(ChapterNode)
  })

  it('maps concept to ConceptNode component', () => {
    expect(nodeTypes.concept).toBe(ConceptNode)
  })

  it('has exactly 2 keys', () => {
    expect(Object.keys(nodeTypes)).toHaveLength(2)
  })

  it('is defined at module level (same reference on repeated import)', async () => {
    const { nodeTypes: nodeTypes2 } = await import('./nodeTypes')
    expect(nodeTypes).toBe(nodeTypes2)
  })
})
