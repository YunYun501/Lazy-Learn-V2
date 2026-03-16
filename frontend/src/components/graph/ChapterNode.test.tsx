import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { describe, it, expect, vi } from 'vitest'
import type { Node, NodeProps } from '@xyflow/react'

import ChapterNode from './ChapterNode'
import type { ConceptNodeData } from '../../types/knowledgeGraph'

vi.mock('@xyflow/react', () => ({
  Handle: ({ position }: { position: string }) => <div data-testid={`handle-${position}`} />,
  Position: { Top: 'top', Bottom: 'bottom' },
}))

type ChapterData = { concept: ConceptNodeData['concept']; isExpanded?: boolean; childCount?: number }
type ChapterFlowNode = Node<ChapterData, 'chapter'>

const mockConcept: ConceptNodeData['concept'] = {
  id: 'ch-1',
  textbookId: 'tb-1',
  title: 'Chapter 1: Introduction',
  nodeType: 'concept',
  level: 'chapter',
  createdAt: '2024-01-01T00:00:00Z',
}

function makeProps(data: ChapterData, selected = false): NodeProps<ChapterFlowNode> {
  return {
    id: 'test-id',
    data,
    type: 'chapter',
    selected,
    dragging: false,
    zIndex: 0,
    selectable: true,
    deletable: true,
    draggable: true,
    isConnectable: true,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
  } as unknown as NodeProps<ChapterFlowNode>
}

describe('ChapterNode', () => {
  it('renders the concept title', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(screen.getByText('Chapter 1: Introduction')).toBeInTheDocument()
  })

  it('shows collapse indicator (▼) when expanded', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept, isExpanded: true })} />)
    expect(screen.getByText('▼')).toBeInTheDocument()
  })

  it('shows expand indicator (▶) when not expanded', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept, isExpanded: false })} />)
    expect(screen.getByText('▶')).toBeInTheDocument()
  })

  it('shows childCount when provided', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept, childCount: 5 })} />)
    expect(screen.getByText('5 concepts')).toBeInTheDocument()
  })

  it('does not show count when childCount is undefined', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(screen.queryByText(/concepts/)).not.toBeInTheDocument()
  })

  it('has graph-node--chapter CSS class', () => {
    const { container } = render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(container.firstChild).toHaveClass('graph-node--chapter')
  })

  it('has graph-node base CSS class', () => {
    const { container } = render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(container.firstChild).toHaveClass('graph-node')
  })

  it('adds graph-node--selected class when selected', () => {
    const { container } = render(<ChapterNode {...makeProps({ concept: mockConcept }, true)} />)
    expect(container.firstChild).toHaveClass('graph-node--selected')
  })

  it('does not have graph-node--selected when not selected', () => {
    const { container } = render(<ChapterNode {...makeProps({ concept: mockConcept }, false)} />)
    expect(container.firstChild).not.toHaveClass('graph-node--selected')
  })

  it('renders top handle', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(screen.getByTestId('handle-top')).toBeInTheDocument()
  })

  it('renders bottom handle', () => {
    render(<ChapterNode {...makeProps({ concept: mockConcept })} />)
    expect(screen.getByTestId('handle-bottom')).toBeInTheDocument()
  })
})
