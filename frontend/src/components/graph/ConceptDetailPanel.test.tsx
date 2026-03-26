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

  it('renders equation breakdown section when components present', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: {
            equation_components: [
              {
                symbol: 'k_a',
                name: 'surface factor',
                type: 'constant',
                description: 'Surface finish effect',
                page_reference: 'p.312',
                linked_node_id: null,
                latex: null,
              },
              {
                symbol: "σ'_e",
                name: 'endurance limit',
                type: 'calculated',
                description: 'Base endurance limit',
                latex: "\\sigma'_e = 0.5 S_{ut}",
                linked_node_id: 'node-linked-1',
                page_reference: null,
              },
            ],
          },
        },
      }),
    )
    const onNavigateToNode = vi.fn()
    render(
      <ConceptDetailPanel
        textbookId="tb-1"
        nodeId="node-1"
        nodes={[]}
        onClose={vi.fn()}
        onNavigateToNode={onNavigateToNode}
      />,
    )
    await waitFor(() => {
      expect(screen.getByText('Equation Breakdown')).toBeInTheDocument()
    })
    expect(screen.getByText('surface factor')).toBeInTheDocument()
    expect(screen.getByText(/p\.312/)).toBeInTheDocument()
  })

  it('hides breakdown section when equation_components is absent', async () => {
    mockGetNodeDetail.mockResolvedValue(makeDetail())
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Pythagorean Theorem')).toBeInTheDocument()
    })
    expect(screen.queryByText('Equation Breakdown')).not.toBeInTheDocument()
  })

  it('hides breakdown section when equation_components is empty array', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: { equation_components: [] },
        },
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Pythagorean Theorem')).toBeInTheDocument()
    })
    expect(screen.queryByText('Equation Breakdown')).not.toBeInTheDocument()
  })

  it('constant variable shows page reference', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: {
            equation_components: [
              {
                symbol: 'k_a',
                name: 'surface factor',
                type: 'constant',
                description: 'Surface finish effect',
                page_reference: 'p.312',
                linked_node_id: null,
                latex: null,
              },
            ],
          },
        },
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Equation Breakdown')).toBeInTheDocument()
    })
    expect(screen.getByText(/p\.312/)).toBeInTheDocument()
    expect(screen.getByText('surface factor')).toBeInTheDocument()
  })

  it('calculated variable with linked_node_id is clickable and calls onNavigateToNode', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: {
            equation_components: [
              {
                symbol: "σ'_e",
                name: 'endurance limit',
                type: 'calculated',
                description: 'Base endurance limit',
                latex: "\\sigma'_e = 0.5 S_{ut}",
                linked_node_id: 'node-linked-1',
                page_reference: null,
              },
            ],
          },
        },
      }),
    )
    const onNavigateToNode = vi.fn()
    render(
      <ConceptDetailPanel
        textbookId="tb-1"
        nodeId="node-1"
        nodes={[]}
        onClose={vi.fn()}
        onNavigateToNode={onNavigateToNode}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('endurance limit')).toBeInTheDocument()
    })

    const listItem = screen.getByText('endurance limit').closest('li')
    expect(listItem).not.toBeNull()
    await userEvent.click(listItem!)
    expect(onNavigateToNode).toHaveBeenCalledWith('node-linked-1')
  })

  it('calculated variable without linked_node_id is not clickable', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: {
            equation_components: [
              {
                symbol: 'S_e',
                name: 'corrected endurance limit',
                type: 'calculated',
                description: 'Endurance limit after corrections',
                latex: 'S_e = k_a k_b S_e^{\\prime}',
                linked_node_id: null,
                page_reference: null,
              },
            ],
          },
        },
      }),
    )
    const onNavigateToNode = vi.fn()
    render(
      <ConceptDetailPanel
        textbookId="tb-1"
        nodeId="node-1"
        nodes={[]}
        onClose={vi.fn()}
        onNavigateToNode={onNavigateToNode}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('corrected endurance limit')).toBeInTheDocument()
    })

    const listItem = screen.getByText('corrected endurance limit').closest('li')
    expect(listItem).not.toBeNull()
    await userEvent.click(listItem!)
    expect(onNavigateToNode).not.toHaveBeenCalled()
  })

  it('invalid latex in calculated component renders fallback without crashing', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        node: {
          ...makeDetail().node,
          metadata: {
            equation_components: [
              {
                symbol: 'x',
                name: 'bad variable',
                type: 'calculated',
                description: 'Has broken LaTeX',
                latex: '\\invalid{unclosed',
                linked_node_id: null,
                page_reference: null,
              },
            ],
          },
        },
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('bad variable')).toBeInTheDocument()
    })
    expect(screen.getByText('Equation Breakdown')).toBeInTheDocument()
  })

  it('renders derivation steps when edge has derivation_steps metadata', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        outgoingEdges: [
          {
            id: 'edge-deriv',
            textbookId: 'tb-1',
            sourceNodeId: 'node-1',
            targetNodeId: 'node-2',
            relationshipType: 'derives_from',
            confidence: 0.9,
            metadata: {
              derivation_steps: ['T_{max} = V_{max}', '\\omega_c^2 = \\sum k_i'],
            },
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('Derivation Steps:')).toBeInTheDocument()
    })
    expect(screen.getAllByText('1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
  })

  it('renders transformation context when edge has transformation_context metadata', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        outgoingEdges: [
          {
            id: 'edge-ctx',
            textbookId: 'tb-1',
            sourceNodeId: 'node-1',
            targetNodeId: 'node-2',
            relationshipType: 'derives_from',
            confidence: 0.9,
            metadata: {
              derivation_steps: ['step1'],
              transformation_context: {
                setting: 'Shaft design with combined bending',
                assumptions: ['DE theory applied'],
                substitutions: [
                  { from: '\\sigma_a', to: "\\sigma'_a", reason: 'DE theory' },
                ],
              },
            },
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
      }),
    )
    render(<ConceptDetailPanel textbookId="tb-1" nodeId="node-1" nodes={[]} onClose={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText(/Shaft design with combined bending/)).toBeInTheDocument()
    })
    expect(screen.getByText(/DE theory applied/)).toBeInTheDocument()
    expect(screen.getAllByText(/DE theory/).length).toBeGreaterThan(0)
  })

  it('does not render derivation section when edge has no metadata', async () => {
    mockGetNodeDetail.mockResolvedValue(
      makeDetail({
        outgoingEdges: [
          {
            id: 'edge-plain',
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
    expect(screen.queryByText('Derivation Steps:')).not.toBeInTheDocument()
  })
})
