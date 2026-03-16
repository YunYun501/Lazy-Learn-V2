import { describe, it, expect } from 'vitest'
import { getEdgeStyle, RELATIONSHIP_LABELS, EDGE_STYLES } from './edgeStyles'
import type { RelationshipType } from '../../types/knowledgeGraph'
import { MarkerType } from '@xyflow/react'

const ALL_RELATIONSHIP_TYPES: RelationshipType[] = [
  'derives_from',
  'proves',
  'prerequisite_of',
  'uses',
  'generalizes',
  'specializes',
  'contradicts',
  'defines',
  'equivalent_form',
]

describe('getEdgeStyle', () => {
  it('returns correct stroke for derives_from', () => {
    const result = getEdgeStyle('derives_from')
    expect(result.style).toBeDefined()
    expect((result.style as { stroke: string }).stroke).toBe('#e94560')
  })

  it('returns correct stroke for contradicts', () => {
    const result = getEdgeStyle('contradicts')
    expect(result.style).toBeDefined()
    expect((result.style as { stroke: string }).stroke).toBe('#ff4444')
  })

  it('returns animated true for contradicts', () => {
    const result = getEdgeStyle('contradicts')
    expect(result.animated).toBe(true)
  })

  it('returns animated false for non-animated types', () => {
    const result = getEdgeStyle('derives_from')
    expect(result.animated).toBe(false)
  })

  it('handles all 9 relationship types without throwing', () => {
    for (const type of ALL_RELATIONSHIP_TYPES) {
      expect(() => getEdgeStyle(type)).not.toThrow()
    }
  })

  it('returns a markerEnd for every type', () => {
    for (const type of ALL_RELATIONSHIP_TYPES) {
      const result = getEdgeStyle(type)
      expect(result.markerEnd).toBeDefined()
    }
  })

  it('returns labelStyle with fontSize 8', () => {
    const result = getEdgeStyle('uses')
    expect(result.labelStyle).toBeDefined()
    expect((result.labelStyle as { fontSize: number }).fontSize).toBe(8)
  })

  it('returns correct stroke for defines', () => {
    const result = getEdgeStyle('defines')
    expect((result.style as { stroke: string }).stroke).toBe('#6dce9e')
  })

  it('returns correct stroke for prerequisite_of', () => {
    const result = getEdgeStyle('prerequisite_of')
    expect((result.style as { stroke: string }).stroke).toBe('#f5a623')
  })

  it('returns ArrowClosed marker for derives_from', () => {
    const result = getEdgeStyle('derives_from')
    expect((result.markerEnd as { type: MarkerType }).type).toBe(MarkerType.ArrowClosed)
  })

  it('returns Arrow marker for uses', () => {
    const result = getEdgeStyle('uses')
    expect((result.markerEnd as { type: MarkerType }).type).toBe(MarkerType.Arrow)
  })
})

describe('RELATIONSHIP_LABELS', () => {
  it('covers all 9 types', () => {
    expect(Object.keys(RELATIONSHIP_LABELS)).toHaveLength(9)
  })

  it('has label for derives_from', () => {
    expect(RELATIONSHIP_LABELS.derives_from).toBe('derives from')
  })

  it('has label for contradicts', () => {
    expect(RELATIONSHIP_LABELS.contradicts).toBe('contradicts')
  })

  it('has label for equivalent_form', () => {
    expect(RELATIONSHIP_LABELS.equivalent_form).toBe('equivalent form')
  })

  it('contains all expected keys', () => {
    for (const type of ALL_RELATIONSHIP_TYPES) {
      expect(RELATIONSHIP_LABELS).toHaveProperty(type)
    }
  })
})

describe('EDGE_STYLES', () => {
  it('has entries for all 9 relationship types', () => {
    expect(Object.keys(EDGE_STYLES)).toHaveLength(9)
  })

  it('contradicts has animated flag', () => {
    expect(EDGE_STYLES.contradicts.animated).toBe(true)
  })

  it('non-contradicts types do not have animated flag', () => {
    const nonAnimated = ALL_RELATIONSHIP_TYPES.filter(t => t !== 'contradicts')
    for (const type of nonAnimated) {
      expect(EDGE_STYLES[type].animated).toBeUndefined()
    }
  })
})
