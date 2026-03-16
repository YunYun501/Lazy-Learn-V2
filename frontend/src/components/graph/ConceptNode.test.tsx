import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import type { Node, NodeProps } from '@xyflow/react'

import ConceptNode from './ConceptNode'
import type { ConceptNodeData } from '../../types/knowledgeGraph'

vi.mock('@xyflow/react', () => ({
  Handle: ({ position }: { position: string }) => <div data-testid={`handle-${position}`} />,
  Position: { Top: 'top', Bottom: 'bottom' },
}))

type ConceptFlowNode = Node<ConceptNodeData, 'concept'>

function makeData(overrides: Partial<ConceptNodeData['concept']> = {}): ConceptNodeData {
  return {
    concept: {
      id: 'node-1',
      textbookId: 'tb-1',
      title: 'Pythagorean Theorem',
      nodeType: 'theorem',
      level: 'section',
      createdAt: '2024-01-01T00:00:00Z',
      ...overrides,
    },
  }
}

function makeProps(data: ConceptNodeData, selected = false): NodeProps<ConceptFlowNode> {
  return {
    id: 'test-id',
    data,
    type: 'concept',
    selected,
    dragging: false,
    zIndex: 0,
    selectable: true,
    deletable: true,
    draggable: true,
    isConnectable: true,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
  } as unknown as NodeProps<ConceptFlowNode>
}

describe('ConceptNode', () => {
  it('renders the concept title', () => {
    render(<ConceptNode {...makeProps(makeData())} />)
    expect(screen.getByText('Pythagorean Theorem')).toBeInTheDocument()
  })

  it('renders the nodeType badge', () => {
    render(<ConceptNode {...makeProps(makeData())} />)
    expect(screen.getByText('theorem')).toBeInTheDocument()
  })

  it('applies graph-node--theorem class for theorem type', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData())} />)
    expect(container.firstChild).toHaveClass('graph-node--theorem')
  })

  it('applies graph-node--definition class for definition type', () => {
    const { container } = render(
      <ConceptNode {...makeProps(makeData({ nodeType: 'definition', title: 'Definition' }))} />,
    )
    expect(container.firstChild).toHaveClass('graph-node--definition')
  })

  it('applies graph-node--equation class for equation type', () => {
    const { container } = render(
      <ConceptNode {...makeProps(makeData({ nodeType: 'equation' }))} />,
    )
    expect(container.firstChild).toHaveClass('graph-node--equation')
  })

  it('applies graph-node--lemma class for lemma type', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData({ nodeType: 'lemma' }))} />)
    expect(container.firstChild).toHaveClass('graph-node--lemma')
  })

  it('applies graph-node--concept class for concept type', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData({ nodeType: 'concept' }))} />)
    expect(container.firstChild).toHaveClass('graph-node--concept')
  })

  it('applies graph-node--example class for example type', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData({ nodeType: 'example' }))} />)
    expect(container.firstChild).toHaveClass('graph-node--example')
  })

  it('shows sourcePage when provided', () => {
    render(<ConceptNode {...makeProps(makeData({ sourcePage: 42 }))} />)
    expect(screen.getByText('p.42')).toBeInTheDocument()
  })

  it('does not show sourcePage when absent', () => {
    render(<ConceptNode {...makeProps(makeData())} />)
    expect(screen.queryByText(/p\./)).not.toBeInTheDocument()
  })

  it('has graph-node base CSS class', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData())} />)
    expect(container.firstChild).toHaveClass('graph-node')
  })

  it('adds graph-node--selected class when selected', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData(), true)} />)
    expect(container.firstChild).toHaveClass('graph-node--selected')
  })

  it('does not have graph-node--selected when not selected', () => {
    const { container } = render(<ConceptNode {...makeProps(makeData(), false)} />)
    expect(container.firstChild).not.toHaveClass('graph-node--selected')
  })

  it('renders top and bottom handles', () => {
    render(<ConceptNode {...makeProps(makeData())} />)
    expect(screen.getByTestId('handle-top')).toBeInTheDocument()
    expect(screen.getByTestId('handle-bottom')).toBeInTheDocument()
  })
})
