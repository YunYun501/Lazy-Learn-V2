import { describe, it, expect } from 'vitest'
import { nodeTypes } from './nodeTypes'
import ChapterNode from './ChapterNode'
import ConceptNode from './ConceptNode'
import EquationNode from './EquationNode'

describe('nodeTypes', () => {
  it('has chapter key', () => {
    expect(nodeTypes).toHaveProperty('chapter')
  })

  it('has concept key', () => {
    expect(nodeTypes).toHaveProperty('concept')
  })

  it('has equation key', () => {
    expect(nodeTypes).toHaveProperty('equation')
  })

  it('maps chapter to ChapterNode component', () => {
    expect(nodeTypes.chapter).toBe(ChapterNode)
  })

  it('maps concept to ConceptNode component', () => {
    expect(nodeTypes.concept).toBe(ConceptNode)
  })

  it('maps equation to EquationNode component', () => {
    expect(nodeTypes.equation).toBe(EquationNode)
  })

  it('has exactly 3 keys', () => {
    expect(Object.keys(nodeTypes)).toHaveLength(3)
  })

  it('is defined at module level (same reference on repeated import)', async () => {
    const { nodeTypes: nodeTypes2 } = await import('./nodeTypes')
    expect(nodeTypes).toBe(nodeTypes2)
  })
})
