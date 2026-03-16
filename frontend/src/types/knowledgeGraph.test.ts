import { describe, it, expect } from 'vitest'
import {
  isValidNodeType,
  isValidRelationshipType,
  type NodeType,
  type RelationshipType,
} from './knowledgeGraph'

describe('isValidNodeType', () => {
  it('returns true for all valid node types', () => {
    const validTypes: NodeType[] = [
      'theorem',
      'definition',
      'equation',
      'lemma',
      'concept',
      'example',
    ]
    validTypes.forEach((type) => {
      expect(isValidNodeType(type)).toBe(true)
    })
  })

  it('returns false for invalid type', () => {
    expect(isValidNodeType('invalid')).toBe(false)
    expect(isValidNodeType('theorem2')).toBe(false)
    expect(isValidNodeType('')).toBe(false)
    expect(isValidNodeType('THEOREM')).toBe(false)
  })
})

describe('isValidRelationshipType', () => {
  it('returns true for all valid relationship types', () => {
    const validTypes: RelationshipType[] = [
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
    validTypes.forEach((type) => {
      expect(isValidRelationshipType(type)).toBe(true)
    })
  })

  it('returns false for invalid type', () => {
    expect(isValidRelationshipType('invalid')).toBe(false)
    expect(isValidRelationshipType('derives')).toBe(false)
    expect(isValidRelationshipType('DERIVES_FROM')).toBe(false)
    expect(isValidRelationshipType('')).toBe(false)
  })
})
