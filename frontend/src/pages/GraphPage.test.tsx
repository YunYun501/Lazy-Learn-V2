import '@testing-library/jest-dom'
import { render, screen, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import GraphPage from './GraphPage'
import { useKnowledgeGraph } from '../hooks/useKnowledgeGraph'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('@xyflow/react', () => ({
  ReactFlow: () => <div data-testid="react-flow" />,
  ReactFlowProvider: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  MiniMap: () => <div data-testid="minimap" />,
  Controls: () => <div data-testid="controls" />,
  Background: () => <div data-testid="background" />,
}))

vi.mock('../components/graph/nodeTypes', () => ({
  nodeTypes: {},
}))

vi.mock('../hooks/useKnowledgeGraph', () => ({
  useKnowledgeGraph: vi.fn(),
}))

let capturedOnNavigateToNode: ((nodeId: string) => void) | undefined
vi.mock('../components/graph/ConceptDetailPanel', () => ({
  ConceptDetailPanel: (props: { onNavigateToNode?: (nodeId: string) => void }) => {
    capturedOnNavigateToNode = props.onNavigateToNode
    return <div data-testid="concept-detail-panel" />
  },
}))

// ── Helpers ───────────────────────────────────────────────────────────────────

const defaultReturn: ReturnType<typeof useKnowledgeGraph> = {
  nodes: [],
  edges: [],
  isLoading: false,
  isGenerating: false,
  progressPct: 0,
  processedChapters: 0,
  totalChapters: 0,
  error: null,
  hasGraph: false,
  selectedNodeId: null,
  setSelectedNodeId: vi.fn(),
  reload: vi.fn(),
}

function renderGraph(textbookId = 'tb_001') {
  return render(
    <MemoryRouter initialEntries={[`/graph/${textbookId}`]}>
      <Routes>
        <Route path="/graph/:textbookId" element={<GraphPage />} />
        <Route path="/" element={<div data-testid="bookshelf">Bookshelf</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('GraphPage', () => {
  beforeEach(() => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({ ...defaultReturn })
  })

  it('test_loading_state_renders_loading_message', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({ ...defaultReturn, isLoading: true })
    renderGraph()
    expect(screen.getByText('Loading knowledge graph...')).toBeInTheDocument()
  })

  it('test_generating_state_renders_progress', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({
      ...defaultReturn,
      isLoading: false,
      isGenerating: true,
      progressPct: 0.5,
      processedChapters: 3,
      totalChapters: 6,
    })
    renderGraph()
    expect(screen.getByText('Generating knowledge graph...')).toBeInTheDocument()
    expect(screen.getByText('Chapter 3 of 6')).toBeInTheDocument()
  })

  it('test_error_state_shows_error_message', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({
      ...defaultReturn,
      isLoading: false,
      error: 'Network failure',
    })
    renderGraph()
    expect(screen.getByText('Error: Network failure')).toBeInTheDocument()
  })

  it('test_no_graph_state_shows_generate_message', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({
      ...defaultReturn,
      isLoading: false,
      hasGraph: false,
    })
    renderGraph()
    expect(screen.getByText('No knowledge graph generated yet.')).toBeInTheDocument()
  })

  it('test_has_graph_renders_react_flow_canvas', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({
      ...defaultReturn,
      isLoading: false,
      hasGraph: true,
      nodes: [{ id: 'n1', type: 'concept', position: { x: 0, y: 0 }, data: {} }],
      edges: [],
    })
    renderGraph()
    expect(screen.getByTestId('react-flow')).toBeInTheDocument()
  })

  it('test_route_registers_graph_textbook_id', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({ ...defaultReturn, isLoading: true })
    renderGraph('textbook-123')
    // Verify that useKnowledgeGraph was called with the route param
    expect(vi.mocked(useKnowledgeGraph)).toHaveBeenCalledWith('textbook-123')
  })

  it('test_invalid_textbook_id_shows_fallback', () => {
    render(
      <MemoryRouter initialEntries={['/graph/']}>
        <Routes>
          <Route path="/graph/:textbookId" element={<GraphPage />} />
          <Route path="/graph/" element={<GraphPage />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Invalid textbook ID')).toBeInTheDocument()
  })

  it('test_onNavigateToNode_wired_to_setSelectedNodeId', () => {
    vi.mocked(useKnowledgeGraph).mockReturnValue({
      ...defaultReturn,
      hasGraph: true,
      nodes: [{ id: 'n1', type: 'concept', position: { x: 0, y: 0 }, data: {} }],
    })
    capturedOnNavigateToNode = undefined
    renderGraph()
    expect(capturedOnNavigateToNode).toBeTypeOf('function')
    act(() => {
      capturedOnNavigateToNode!('node-target')
    })
    expect(defaultReturn.setSelectedNodeId).toHaveBeenCalledWith('node-target')
  })
})
