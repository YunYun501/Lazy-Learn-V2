import { RELATIONSHIP_LABELS } from './edgeStyles'
import type { RelationshipType } from '../../types/knowledgeGraph'

const LEGEND_COLORS: Record<RelationshipType, string> = {
  derives_from: '#e94560',
  proves: '#e94560',
  prerequisite_of: '#f5a623',
  uses: '#888888',
  generalizes: '#5b9cf6',
  specializes: '#5b9cf6',
  contradicts: '#ff4444',
  defines: '#6dce9e',
  equivalent_form: '#f5a623',
}

export function GraphLegend() {
  return (
    <div className="graph-legend" data-testid="graph-legend">
      <div style={{ marginBottom: 4, fontSize: 7, fontFamily: 'monospace', color: '#aaa' }}>LEGEND</div>
      {(Object.keys(RELATIONSHIP_LABELS) as RelationshipType[]).map(type => (
        <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
          <div style={{ width: 16, height: 2, background: LEGEND_COLORS[type] }} />
          <span style={{ fontSize: 6, fontFamily: 'monospace', color: '#ccc' }}>
            {RELATIONSHIP_LABELS[type]}
          </span>
        </div>
      ))}
    </div>
  )
}
