import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import type { Node, NodeProps } from '@xyflow/react'

import EquationNode from './EquationNode'
import type { ConceptNodeData } from '../../types/knowledgeGraph'

vi.mock('@xyflow/react', () => ({
  Handle: ({ position }: { position: string }) => <div data-testid={`handle-${position}`} />,
  Position: { Top: 'top', Bottom: 'bottom' },
}))

vi.mock('react-katex', () => ({
  InlineMath: ({ math }: { math: string }) => <span data-testid="inline-math">{math}</span>,
}))

type EquationFlowNode = Node<ConceptNodeData, 'equation'>

function makeData(overrides: Partial<ConceptNodeData['concept']> = {}): ConceptNodeData {
  return {
    concept: {
      id: 'eq-1',
      textbookId: 'tb-1',
      title: 'Energy-Mass Equivalence',
      nodeType: 'equation',
      level: 'equation',
      createdAt: '2024-01-01T00:00:00Z',
      ...overrides,
    },
  }
}

function makeProps(data: ConceptNodeData, selected = false): NodeProps<EquationFlowNode> {
  return {
    id: 'test-id',
    data,
    type: 'equation',
    selected,
    dragging: false,
    zIndex: 0,
    selectable: true,
    deletable: true,
    draggable: true,
    isConnectable: true,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
  } as unknown as NodeProps<EquationFlowNode>
}

describe('EquationNode', () => {
  it('has graph-node--equation CSS class', () => {
    const { container } = render(<EquationNode {...makeProps(makeData())} />)
    expect(container.firstChild).toHaveClass('graph-node--equation')
  })

  it('has graph-node base CSS class', () => {
    const { container } = render(<EquationNode {...makeProps(makeData())} />)
    expect(container.firstChild).toHaveClass('graph-node')
  })

  it('renders InlineMath when latex metadata is present', () => {
    const data = makeData({ metadata: { latex: 'E = mc^2' } })
    render(<EquationNode {...makeProps(data)} />)
    expect(screen.getByTestId('inline-math')).toBeInTheDocument()
    expect(screen.getByText('E = mc^2')).toBeInTheDocument()
  })

  it('renders title when no latex metadata', () => {
    render(<EquationNode {...makeProps(makeData())} />)
    expect(screen.getByText('Energy-Mass Equivalence')).toBeInTheDocument()
  })

  it('renders title when metadata exists but no latex key', () => {
    const data = makeData({ metadata: { other: 'value' } })
    render(<EquationNode {...makeProps(data)} />)
    expect(screen.getByText('Energy-Mass Equivalence')).toBeInTheDocument()
  })

  it('shows sourcePage when provided', () => {
    render(<EquationNode {...makeProps(makeData({ sourcePage: 99 }))} />)
    expect(screen.getByText('p.99')).toBeInTheDocument()
  })

  it('does not show sourcePage when absent', () => {
    render(<EquationNode {...makeProps(makeData())} />)
    expect(screen.queryByText(/p\./)).not.toBeInTheDocument()
  })

  it('adds graph-node--selected class when selected', () => {
    const { container } = render(<EquationNode {...makeProps(makeData(), true)} />)
    expect(container.firstChild).toHaveClass('graph-node--selected')
  })

  it('does not have graph-node--selected when not selected', () => {
    const { container } = render(<EquationNode {...makeProps(makeData(), false)} />)
    expect(container.firstChild).not.toHaveClass('graph-node--selected')
  })

  it('renders top and bottom handles', () => {
    render(<EquationNode {...makeProps(makeData())} />)
    expect(screen.getByTestId('handle-top')).toBeInTheDocument()
    expect(screen.getByTestId('handle-bottom')).toBeInTheDocument()
  })
})
