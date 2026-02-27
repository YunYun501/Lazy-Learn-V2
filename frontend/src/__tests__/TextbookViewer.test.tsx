import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { TextbookViewer } from '../components/TextbookViewer'

const MOCK_CHAPTER = {
  textbook_id: 'tb1',
  chapter_num: '3',
  title: 'Chapter 3: The Z-Transform',
  text: 'The Z-transform is defined as $X(z) = \\sum_{n=-\\infty}^{\\infty} x[n] z^{-n}$.',
  image_urls: [
    'http://localhost:8000/api/textbooks/tb1/images/page3_img0.png',
    'http://localhost:8000/api/textbooks/tb1/images/page4_img0.png',
  ],
  page_start: 45,
  page_end: 62,
}

describe('TextbookViewer', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows loading state while fetching', () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {}))

    render(<TextbookViewer textbookId="tb1" chapterNum="3" />)

    expect(screen.getByTestId('textbook-viewer-loading')).toBeInTheDocument()
  })

  it('renders chapter title and text after loading', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_CHAPTER),
    } as unknown as Response)

    render(<TextbookViewer textbookId="tb1" chapterNum="3" />)

    await waitFor(() => {
      expect(screen.getByTestId('textbook-viewer')).toBeInTheDocument()
    })

    expect(screen.getByTestId('chapter-title')).toHaveTextContent(
      'Chapter 3: The Z-Transform'
    )
    expect(screen.getByTestId('chapter-text')).toBeInTheDocument()
  })

  it('renders images with navigation controls', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_CHAPTER),
    } as unknown as Response)

    render(<TextbookViewer textbookId="tb1" chapterNum="3" />)

    await waitFor(() => {
      expect(screen.getByTestId('chapter-images')).toBeInTheDocument()
    })

    expect(screen.getByTestId('chapter-image')).toBeInTheDocument()
    expect(screen.getByTestId('image-counter')).toHaveTextContent('1 / 2')
  })

  it('navigates between images with next/prev buttons', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_CHAPTER),
    } as unknown as Response)

    render(<TextbookViewer textbookId="tb1" chapterNum="3" />)

    await waitFor(() => {
      expect(screen.getByTestId('chapter-images')).toBeInTheDocument()
    })

    // Click Next
    fireEvent.click(screen.getByText('Next →'))
    expect(screen.getByTestId('image-counter')).toHaveTextContent('2 / 2')

    // Click Prev
    fireEvent.click(screen.getByText('← Prev'))
    expect(screen.getByTestId('image-counter')).toHaveTextContent('1 / 2')
  })

  it('shows error state on fetch failure', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      statusText: 'Not Found',
    } as unknown as Response)

    render(<TextbookViewer textbookId="tb1" chapterNum="999" />)

    await waitFor(() => {
      expect(screen.getByTestId('textbook-viewer-error')).toBeInTheDocument()
    })
  })
})
