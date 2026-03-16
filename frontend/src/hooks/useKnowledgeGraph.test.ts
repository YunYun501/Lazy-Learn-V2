import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useKnowledgeGraph } from './useKnowledgeGraph'
import * as knowledgeGraphApi from '../api/knowledgeGraph'
import type { GraphStatusResponse, GraphData } from '../types/knowledgeGraph'

vi.mock('../api/knowledgeGraph')
vi.mock('./useGraphLayout', () => ({
  computeLayout: (nodes: unknown[], edges: unknown[]) => ({ nodes, edges }),
}))

const mockGetGraphStatus = vi.mocked(knowledgeGraphApi.getGraphStatus)
const mockPollGraphStatus = vi.mocked(knowledgeGraphApi.pollGraphStatus)
const mockGetGraphData = vi.mocked(knowledgeGraphApi.getGraphData)

function makeStatus(overrides: Partial<GraphStatusResponse> = {}): GraphStatusResponse {
  return {
    jobId: 'job-1',
    textbookId: 'tb-1',
    status: 'processing',
    progressPct: 0.5,
    processedChapters: 3,
    totalChapters: 6,
    ...overrides,
  }
}

function makeGraphData(): GraphData {
  return {
    textbookId: 'tb-1',
    nodes: [],
    edges: [],
  }
}

describe('useKnowledgeGraph polling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('test_starts_polling_when_status_is_processing', async () => {
    const processingStatus = makeStatus()
    const completedStatus = makeStatus({ status: 'completed', progressPct: 1 })

    mockGetGraphStatus.mockResolvedValue(processingStatus)
    mockPollGraphStatus.mockResolvedValue(completedStatus)
    mockGetGraphData.mockResolvedValue(makeGraphData())

    const { result } = renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(mockPollGraphStatus).toHaveBeenCalledWith(
        'tb-1',
        2000,
        expect.any(Function)
      )
    })

    expect(result.current.isGenerating).toBe(true)
  })

  it('test_auto_reloads_after_processing_completes', async () => {
    const processingStatus = makeStatus()
    const completedStatus = makeStatus({ status: 'completed', progressPct: 1 })
    const graphData = makeGraphData()

    mockGetGraphStatus
      .mockResolvedValueOnce(processingStatus)
      .mockResolvedValueOnce(completedStatus)
    mockPollGraphStatus.mockResolvedValue(completedStatus)
    mockGetGraphData.mockResolvedValue(graphData)

    renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(mockGetGraphData).toHaveBeenCalled()
    })

    expect(mockGetGraphData).toHaveBeenCalledWith('tb-1')
  })

  it('test_shows_error_when_generation_fails', async () => {
    const processingStatus = makeStatus()
    const failedStatus = makeStatus({ status: 'failed', error: 'LLM timeout' })

    mockGetGraphStatus.mockResolvedValue(processingStatus)
    mockPollGraphStatus.mockResolvedValue(failedStatus)

    const { result } = renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(result.current.error).toBe('LLM timeout')
    })

    expect(result.current.isGenerating).toBe(false)
  })

  it('test_shows_fallback_error_when_generation_fails_without_message', async () => {
    const processingStatus = makeStatus()
    const failedStatus = makeStatus({ status: 'failed', error: undefined })

    mockGetGraphStatus.mockResolvedValue(processingStatus)
    mockPollGraphStatus.mockResolvedValue(failedStatus)

    const { result } = renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(result.current.error).toBe('Graph generation failed')
    })
  })

  it('test_shows_error_when_poll_throws', async () => {
    const processingStatus = makeStatus()

    mockGetGraphStatus.mockResolvedValue(processingStatus)
    mockPollGraphStatus.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(result.current.error).toBe('Failed to track graph generation progress')
    })

    expect(result.current.isGenerating).toBe(false)
  })

  it('test_updates_progress_via_onProgress_callback', async () => {
    const processingStatus = makeStatus({ progressPct: 0.2, processedChapters: 1 })
    const completedStatus = makeStatus({ status: 'completed', progressPct: 1 })

    mockGetGraphStatus.mockResolvedValue(processingStatus)
    mockGetGraphData.mockResolvedValue(makeGraphData())

    let capturedCallback: ((s: GraphStatusResponse) => void) | null = null
    mockPollGraphStatus.mockImplementation((_id, _ms, onProgress) => {
      capturedCallback = onProgress
      return Promise.resolve(completedStatus)
    })

    const { result } = renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(capturedCallback).not.toBeNull()
    })

    act(() => {
      capturedCallback!(makeStatus({ progressPct: 0.7, processedChapters: 4 }))
    })

    expect(result.current.progressPct).toBe(0.7)
    expect(result.current.processedChapters).toBe(4)
  })

  it('test_does_not_poll_when_status_is_completed', async () => {
    const completedStatus = makeStatus({ status: 'completed' })

    mockGetGraphStatus.mockResolvedValue(completedStatus)
    mockGetGraphData.mockResolvedValue(makeGraphData())

    renderHook(() => useKnowledgeGraph('tb-1'))

    await waitFor(() => {
      expect(mockGetGraphData).toHaveBeenCalled()
    })

    expect(mockPollGraphStatus).not.toHaveBeenCalled()
  })
})
