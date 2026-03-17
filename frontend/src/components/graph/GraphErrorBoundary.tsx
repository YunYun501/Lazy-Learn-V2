import { Component, type ReactNode } from 'react'
import { logger } from '../../services/logger'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class GraphErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    logger.error(`Graph rendering crashed: ${error.message}`, {
      component: 'GraphErrorBoundary',
      error,
      context: info.componentStack ?? undefined,
    })
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="graph-progress" data-testid="graph-error-boundary">
          <div>Graph rendering failed.</div>
          <div style={{ fontSize: '0.8em', color: '#888' }}>
            Try going back and regenerating the knowledge graph.
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
