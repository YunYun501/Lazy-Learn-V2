import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ExplanationView } from '../components/ExplanationView'

const CHAPTERS = [
  {
    textbook_id: 'tb1',
    chapter_num: '3',
    classification: 'EXPLAINS',
    textbook_title: 'Digital Control Systems',
  },
]

// Helper to create a mock SSE ReadableStream
function makeSseStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(`data: ${chunk}\n\n`))
      }
      controller.enqueue(encoder.encode('data: [DONE]\n\n'))
      controller.close()
    },
  })
}

describe('ExplanationView', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows loading state initially when chapters provided', async () => {
    const mockFetch = vi.mocked(fetch)
    // Never resolves — stays in loading
    mockFetch.mockReturnValue(new Promise(() => {}))

    render(
      <ExplanationView chapters={CHAPTERS} query="Explain Z-transform" />
    )

    expect(screen.getByTestId('explanation-loading')).toBeInTheDocument()
  })

  it('renders streamed content progressively', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({
      ok: true,
      body: makeSseStream(['The Z-transform ', 'is defined as...']),
    } as unknown as Response)

    render(
      <ExplanationView chapters={CHAPTERS} query="Explain Z-transform" />
    )

    await waitFor(() => {
      expect(screen.getByTestId('explanation-content')).toBeInTheDocument()
    })

    // Content should contain the streamed text
    expect(screen.getByTestId('explanation-content')).toHaveTextContent(
      'The Z-transform'
    )
  })

  it('shows source citations as clickable elements', async () => {
    const onSourceClick = vi.fn()
    const mockFetch = vi.mocked(fetch)
    // Include a source citation in the streamed content
    mockFetch.mockResolvedValue({
      ok: true,
      body: makeSseStream(['[Source: Digital Control Systems, Ch.3]']),
    } as unknown as Response)

    render(
      <ExplanationView
        chapters={CHAPTERS}
        query="Explain Z-transform"
        onSourceClick={onSourceClick}
      />
    )

    await waitFor(() => {
      expect(screen.getByTestId('explanation-content')).toBeInTheDocument()
    })

    // Source citation text should be visible
    expect(screen.getByTestId('explanation-content')).toHaveTextContent(
      'Source: Digital Control Systems, Ch.3'
    )
  })

  it('shows error state on fetch failure', async () => {
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockRejectedValue(new Error('Network error'))

    render(
      <ExplanationView chapters={CHAPTERS} query="Explain Z-transform" />
    )

    await waitFor(() => {
      expect(screen.getByTestId('explanation-error')).toBeInTheDocument()
    })
  })

  it('shows Generate Practice button after streaming completes', async () => {
    const onGeneratePractice = vi.fn()
    const mockFetch = vi.mocked(fetch)
    mockFetch.mockResolvedValue({
      ok: true,
      body: makeSseStream(['Explanation complete.']),
    } as unknown as Response)

    render(
      <ExplanationView
        chapters={CHAPTERS}
        query="Explain Z-transform"
        onGeneratePractice={onGeneratePractice}
      />
    )

    await waitFor(() => {
      expect(screen.getByTestId('explanation-actions')).toBeInTheDocument()
    })
  })
})
