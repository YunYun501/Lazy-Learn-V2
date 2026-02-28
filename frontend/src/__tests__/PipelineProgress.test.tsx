import '@testing-library/jest-dom'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { PipelineProgress } from '../components/PipelineProgress'
import type { PipelineStatus, ChapterWithStatus } from '../types/pipeline'
import * as pipelineApi from '../api/pipeline'

// ── Mock the pipeline API ─────────────────────────────────────────────────
vi.mock('../api/pipeline', () => ({
  getExtractionProgress: vi.fn(),
  extractDeferred: vi.fn(),
  getTextbookStatus: vi.fn(),
  verifyChapters: vi.fn(),
}))

// ── Mock data ─────────────────────────────────────────────────────────────

const mockChaptersExtracting: ChapterWithStatus[] = [
  {
    id: 'ch-1',
    title: 'Introduction',
    chapter_number: 1,
    page_start: 1,
    page_end: 20,
    extraction_status: 'extracting',
  },
  {
    id: 'ch-2',
    title: 'Fundamentals',
    chapter_number: 2,
    page_start: 21,
    page_end: 50,
    extraction_status: 'extracted',
  },
]

const mockChaptersDeferred: ChapterWithStatus[] = [
  {
    id: 'ch-1',
    title: 'Introduction',
    chapter_number: 1,
    page_start: 1,
    page_end: 20,
    extraction_status: 'extracted',
  },
  {
    id: 'ch-2',
    title: 'Advanced Topics',
    chapter_number: 2,
    page_start: 21,
    page_end: 50,
    extraction_status: 'deferred',
  },
]

const mockChaptersComplete: ChapterWithStatus[] = [
  {
    id: 'ch-1',
    title: 'Introduction',
    chapter_number: 1,
    page_start: 1,
    page_end: 20,
    extraction_status: 'extracted',
  },
  {
    id: 'ch-2',
    title: 'Fundamentals',
    chapter_number: 2,
    page_start: 21,
    page_end: 50,
    extraction_status: 'extracted',
  },
]

// ── Render helper ─────────────────────────────────────────────────────────

function renderPipelineProgress(
  initialStatus: PipelineStatus = 'extracting',
  chapters: ChapterWithStatus[] = mockChaptersExtracting,
  textbookId: string = 'tb-123',
) {
  return render(
    <MemoryRouter>
      <Routes>
        <Route
          path="/"
          element={
            <PipelineProgress
              textbookId={textbookId}
              initialStatus={initialStatus}
              chapters={chapters}
            />
          }
        />
      </Routes>
    </MemoryRouter>
  )
}

// ── Cleanup ───────────────────────────────────────────────────────────────

afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

// ── Test suite ────────────────────────────────────────────────────────────

describe('PipelineProgress', () => {
  it('test_shows_extraction_progress', async () => {
    renderPipelineProgress('extracting', mockChaptersExtracting)

    expect(await screen.findByText('Introduction')).toBeInTheDocument()
    expect(screen.getByText('Fundamentals')).toBeInTheDocument()
  })

  it('test_shows_completed_state', async () => {
    renderPipelineProgress('fully_extracted', mockChaptersComplete)

    expect(await screen.findByText('Extraction complete')).toBeInTheDocument()
  })

  it('test_shows_deferred_chapters', async () => {
    renderPipelineProgress('partially_extracted', mockChaptersDeferred)

    expect(await screen.findByText('Advanced Topics')).toBeInTheDocument()
    expect(screen.getByText('Introduction')).toBeInTheDocument()
  })

  it('test_extract_remaining_button', async () => {
    renderPipelineProgress('partially_extracted', mockChaptersDeferred)

    expect(await screen.findByText('Extract remaining chapters')).toBeInTheDocument()
  })

  it('test_extract_remaining_calls_api', async () => {
    ;(pipelineApi.extractDeferred as any).mockResolvedValue({ status: 'ok' })
    ;(pipelineApi.getExtractionProgress as any).mockResolvedValue({
      pipeline_status: 'extracting' as PipelineStatus,
      chapters: mockChaptersDeferred,
    })

    renderPipelineProgress('partially_extracted', mockChaptersDeferred)

    fireEvent.click(await screen.findByText('Extract remaining chapters'))

    await waitFor(() => {
      expect(pipelineApi.extractDeferred).toHaveBeenCalledWith('tb-123', ['ch-2'])
    })
  })

  it('test_error_chapter_shown', async () => {
    const chaptersWithError: ChapterWithStatus[] = [
      {
        id: 'ch-1',
        title: 'Failed Chapter',
        chapter_number: 1,
        page_start: 1,
        page_end: 20,
        extraction_status: 'error',
      },
    ]
    renderPipelineProgress('extracting', chaptersWithError)

    expect(await screen.findByText('Failed Chapter')).toBeInTheDocument()
    expect(screen.getByText('✗')).toBeInTheDocument()
  })

  it('test_polls_for_progress', async () => {
    vi.useFakeTimers()

    ;(pipelineApi.getExtractionProgress as any).mockResolvedValue({
      pipeline_status: 'extracting' as PipelineStatus,
      chapters: mockChaptersExtracting,
    })

    renderPipelineProgress('extracting', mockChaptersExtracting)

    // Advance timer to trigger the first polling interval
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })

    expect(pipelineApi.getExtractionProgress).toHaveBeenCalledWith('tb-123')
  })
})
