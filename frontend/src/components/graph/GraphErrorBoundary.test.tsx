import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GraphErrorBoundary } from './GraphErrorBoundary'

// Suppress console.error for expected error boundary output
const originalConsoleError = console.error

beforeEach(() => {
  console.error = vi.fn()
})

afterEach(() => {
  console.error = originalConsoleError
})

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('ReactFlow render crash')
  }
  return <div data-testid="child-content">Graph content</div>
}

describe('GraphErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <GraphErrorBoundary>
        <ThrowingChild shouldThrow={false} />
      </GraphErrorBoundary>,
    )
    expect(screen.getByTestId('child-content')).toBeInTheDocument()
    expect(screen.getByText('Graph content')).toBeInTheDocument()
  })

  it('renders fallback UI when child throws', () => {
    render(
      <GraphErrorBoundary>
        <ThrowingChild shouldThrow={true} />
      </GraphErrorBoundary>,
    )
    expect(screen.getByTestId('graph-error-boundary')).toBeInTheDocument()
    expect(screen.getByText('Graph rendering failed.')).toBeInTheDocument()
    expect(
      screen.getByText('Try going back and regenerating the knowledge graph.'),
    ).toBeInTheDocument()
  })

  it('renders custom fallback when provided and child throws', () => {
    render(
      <GraphErrorBoundary fallback={<div data-testid="custom-fallback">Custom error</div>}>
        <ThrowingChild shouldThrow={true} />
      </GraphErrorBoundary>,
    )
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument()
    expect(screen.getByText('Custom error')).toBeInTheDocument()
    expect(screen.queryByTestId('graph-error-boundary')).not.toBeInTheDocument()
  })

  it('does not render error UI when no error occurs', () => {
    render(
      <GraphErrorBoundary>
        <ThrowingChild shouldThrow={false} />
      </GraphErrorBoundary>,
    )
    expect(screen.queryByTestId('graph-error-boundary')).not.toBeInTheDocument()
  })
})
