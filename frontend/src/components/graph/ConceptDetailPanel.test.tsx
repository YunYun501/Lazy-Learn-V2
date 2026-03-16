import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'

import { ConceptDetailPanel } from './ConceptDetailPanel'
import { getNodeDetail } from '../../api/knowledgeGraph'
import type { ConceptNodeDetail } from '../../types/knowledgeGraph'

vi.mock('../../api/knowledgeGraph', () => ({
  getNodeDetail: vi.fn(),
}))

const mockGetNodeDetail = getNodeDetail as Mock

function makeDetail(overrides: Partial<ConceptNodeDetail> = {}): ConceptNodeDetail {
  return {
    node: {
      id: 'node-1',
      textbookId: 'tb-1',
      title: 'Pythagorean Theorem',
      description: 'A theorem about right triangles.',
      nodeType: 'theorem',
      level: 'section',
      sourcePage: 42,
      createdAt: '2024-01-01T00:00:00Z',
    },
    incomingEdges: [],
    outgoingEdges: [],
    ...overrides,
  }
}

describe('ConceptDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders null when nodeId is null', () => {
    const { container } = render(
      <ConceptDetailPanel textbookId="tb-1" nodeId={null} nodes={[]} onClose={vi.fn()} />,
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders panel when nodeId is provided', async () => {
    mockGetNodeDetail.mockResolvedValue(makeDetail())
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)
    expect(screen.getByTestId('concept-detail-panel')).toBeInTheDocument()
  })

  it('shows loading state then concept details', async () => {
    mockGetNodeDetail.mockResolvedValue(makeDetail())
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    // Initially loading
    expect(screen.getByText('Loading...')).toBeInTheDocument()

    // After data loads
    await waitFor(() => {
      expect(screen.getByText('Pythagorean Theorem')).toBeInTheDocument()
    })
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    expect(screen.getByText('theorem')).toBeInTheDocument()
    expect(screen.getByText('A theorem about right triangles.')).toBeInTheDocument()
    expect(screen.getByText('Found in: Page 42')).toBeInTheDocument()
  })

  it('close button calls onClose', async () => {
    mockGetNodeDetail.mockResolvedValue(makeDetail())
    const onClose = vi.fn()
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={onClose} />)

    const closeBtn = screen.getByRole('button', { name: /close/i })
    await userEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('shows error message when API call fails', async () => {
    mockGetNodeDetail.mockRejectedValue(new Error('Network error'))
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Error: Network error')).toBeInTheDocument()
    })
  })

  it('renders outgoing edges when present', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        outgoingEdges: [
          {
            id: 'edge-1',
            textbookId: 'tb-1',
            sourceNodeId: 'node-1',
            targetNodeId: 'node-2',
            relationshipType: 'derives_from',
            confidence: 0.9,
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Relationships')).toBeInTheDocument()
    })
    expect(screen.getByText('derives from')).toBeInTheDocument()
    expect(screen.getByText('node-2')).toBeInTheDocument()
  })

  it('renders incoming edges when present', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        incomingEdges: [
          {
            id: 'edge-2',
            textbookId: 'tb-1',
            sourceNodeId: 'node-3',
            targetNodeId: 'node-1',
            relationshipType: 'uses',
            confidence: 0.8,
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Used by')).toBeInTheDocument()
    })
    expect(screen.getByText('node-3')).toBeInTheDocument()
    expect(screen.getByText('uses')).toBeInTheDocument()
  })

  it('does not show description section when description is absent', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({ node: { ...makeDetail().node, description: undefined } }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Pythagorean Theorem')).toBeInTheDocument()
    })
    expect(
      screen.queryByText('A theorem about right triangles.'),
    ).not.toBeInTheDocument()
  })
})
