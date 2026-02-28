import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  getTextbookStatus,
  verifyChapters,
  extractDeferred,
  getExtractionProgress,
} from '../api/pipeline'
import type { ChapterWithStatus } from '../types/pipeline'

// ── Mock global fetch ────────────────────────────────────────────────────

const mockFetch = vi.fn()
global.fetch = mockFetch as any

// ── Test suite ───────────────────────────────────────────────────────────

describe('Pipeline API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Test 1: getTextbookStatus ────────────────────────────────────────

  it('test_getTextbookStatus_calls_correct_url', async () => {
    const mockChapters: ChapterWithStatus[] = [
      {
        id: 'ch-1',
        title: 'Chapter 1',
        chapter_number: 1,
        page_start: 1,
        page_end: 50,
        extraction_status: 'pending',
      },
    ]

    const mockResponse = {
      pipeline_status: 'awaiting_verification' as const,
      chapters: mockChapters,
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await getTextbookStatus('textbook-123')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/textbooks/textbook-123/status'
    )
    expect(result).toEqual(mockResponse)
  })

  // ── Test 2: verifyChapters ──────────────────────────────────────────

  it('test_verifyChapters_sends_selected_ids', async () => {
    const selectedIds = ['ch-1', 'ch-2']
    const mockResponse = {
      status: 'verified',
      selected_count: 2,
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await verifyChapters('textbook-123', selectedIds)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/textbooks/textbook-123/verify-chapters',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_chapter_ids: selectedIds }),
      }
    )
    expect(result).toEqual(mockResponse)
  })

  // ── Test 3: extractDeferred ─────────────────────────────────────────

  it('test_extractDeferred_sends_chapter_ids', async () => {
    const chapterIds = ['ch-3', 'ch-4']
    const mockResponse = {
      status: 'extraction_started',
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await extractDeferred('textbook-123', chapterIds)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/textbooks/textbook-123/extract-deferred',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_ids: chapterIds }),
      }
    )
    expect(result).toEqual(mockResponse)
  })

  // ── Test 4: getExtractionProgress ───────────────────────────────────

  it('test_getExtractionProgress_returns_chapters', async () => {
    const mockChapters: ChapterWithStatus[] = [
      {
        id: 'ch-1',
        title: 'Chapter 1',
        chapter_number: 1,
        page_start: 1,
        page_end: 50,
        extraction_status: 'extracting',
      },
      {
        id: 'ch-2',
        title: 'Chapter 2',
        chapter_number: 2,
        page_start: 51,
        page_end: 100,
        extraction_status: 'extracted',
      },
    ]

    const mockResponse = {
      pipeline_status: 'extracting' as const,
      chapters: mockChapters,
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const result = await getExtractionProgress('textbook-123')

    expect(mockFetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/textbooks/textbook-123/extraction-progress'
    )
    expect(result).toEqual(mockResponse)
  })
})
