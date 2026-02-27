import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BookshelfPage } from '../pages/BookshelfPage'
import * as textbooksApi from '../api/textbooks'

// Mock the API
vi.mock('../api/textbooks', () => ({
  getTextbooks: vi.fn(),
  importTextbook: vi.fn(),
  getImportStatus: vi.fn(),
}))

function renderBookshelf() {
  return render(
    <MemoryRouter>
      <BookshelfPage />
    </MemoryRouter>
  )
}

describe('BookshelfPage', () => {
  beforeEach(() => {
    vi.mocked(textbooksApi.getTextbooks).mockResolvedValue([])
  })

  it('renders the bookshelf page with title', async () => {
    renderBookshelf()
    expect(screen.getByText('LAZY LEARN')).toBeInTheDocument()
  })

  it('renders import button', async () => {
    renderBookshelf()
    expect(screen.getByText('+ IMPORT TEXTBOOK')).toBeInTheDocument()
  })

  it('renders textbook list from API response', async () => {
    vi.mocked(textbooksApi.getTextbooks).mockResolvedValue([
      {
        id: 'tb_001',
        title: 'Digital Control Systems',
        filepath: '/data/tb_001/original.pdf',
        course: 'MECH0089',
        library_type: 'course',
        processed_at: null,
      },
    ])
    renderBookshelf()
    // Wait for async load
    const book = await screen.findByTestId('book-spine')
    expect(book).toBeInTheDocument()
  })

  it('renders shelf sections for math library and course books', () => {
    renderBookshelf()
    expect(screen.getByText('MATH LIBRARY')).toBeInTheDocument()
    expect(screen.getByText('COURSE BOOKS')).toBeInTheDocument()
  })
})
