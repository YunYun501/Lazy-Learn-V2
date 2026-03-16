import type { RelationshipType } from '../../types/knowledgeGraph'
import { MarkerType } from '@xyflow/react'
import type { Edge } from '@xyflow/react'

interface EdgeStyle {
  stroke: string
  strokeWidth: number
  strokeDasharray?: string
  animated?: boolean
}

interface EdgeConfig {
  style: EdgeStyle
  markerEnd: { type: MarkerType; color: string }
  label?: string
  labelStyle?: Record<string, string | number>
  className?: string
  animated?: boolean
}

const EDGE_STYLES: Record<RelationshipType, EdgeConfig> = {
  derives_from: {
    style: { stroke: '#e94560', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#e94560' },
  },
  proves: {
    style: { stroke: '#e94560', strokeWidth: 3 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#e94560' },
  },
  prerequisite_of: {
    style: { stroke: '#f5a623', strokeWidth: 2, strokeDasharray: '6 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f5a623' },
  },
  uses: {
    style: { stroke: '#888888', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.Arrow, color: '#888888' },
  },
  generalizes: {
    style: { stroke: '#5b9cf6', strokeWidth: 2, strokeDasharray: '3 3' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#5b9cf6' },
  },
  specializes: {
    style: { stroke: '#5b9cf6', strokeWidth: 1.5, strokeDasharray: '3 3' },
    markerEnd: { type: MarkerType.Arrow, color: '#5b9cf6' },
  },
  contradicts: {
    style: { stroke: '#ff4444', strokeWidth: 2.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#ff4444' },
    animated: true,
  },
  defines: {
    style: { stroke: '#6dce9e', strokeWidth: 2.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#6dce9e' },
  },
  equivalent_form: {
    style: { stroke: '#f5a623', strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#f5a623' },
  },
}

export function getEdgeStyle(relationshipType: RelationshipType): Partial<Edge> {
  const config = EDGE_STYLES[relationshipType] ?? EDGE_STYLES.uses
  return {
    style: config.style,
    markerEnd: config.markerEnd,
    animated: config.animated ?? false,
    labelStyle: { fontSize: 8, fill: '#888', fontFamily: 'monospace' },
  }
}

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  derives_from: 'derives from',
  proves: 'proves',
  prerequisite_of: 'prerequisite of',
  uses: 'uses',
  generalizes: 'generalizes',
  specializes: 'specializes',
  contradicts: 'contradicts',
  defines: 'defines',
  equivalent_form: 'equivalent form',
}

export { EDGE_STYLES }
