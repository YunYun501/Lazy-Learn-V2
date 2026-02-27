import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { SearchResults } from '../components/SearchResults'
import type { CategorizedMatch } from '../api/search'

const EXPLAINS_MATCH: CategorizedMatch = {
  source: 'Digital Control Systems',
  chapter: 'Chapter 3: The Z-Transform',
  subchapter: '3.1',
  classification: 'EXPLAINS',
  confidence: 0.95,
  reason: 'This chapter introduces and derives the Z-transform.',
  textbook_id: 'tb1',
  chapter_num: '3',
}

const USES_MATCH: CategorizedMatch = {
  source: 'Digital Control Systems',
  chapter: 'Chapter 5: Stability Analysis',
  subchapter: '5.2',
  classification: 'USES',
  confidence: 0.7,
  reason: 'Uses Z-transform for pole-zero analysis.',
  textbook_id: 'tb1',
  chapter_num: '5',
}

describe('SearchResults', () => {
  it('renders EXPLAINS badge with correct type', () => {
    render(
      <SearchResults
        query="Z-transform"
        matches={[EXPLAINS_MATCH]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
      />
    )
    expect(screen.getByTestId('badge-EXPLAINS')).toBeInTheDocument()
    expect(screen.getByTestId('badge-EXPLAINS')).toHaveTextContent('EXPLAINS')
  })

  it('renders USES badge with correct type', () => {
    render(
      <SearchResults
        query="Z-transform"
        matches={[USES_MATCH]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
      />
    )
    expect(screen.getByTestId('badge-USES')).toBeInTheDocument()
    expect(screen.getByTestId('badge-USES')).toHaveTextContent('USES')
  })

  it('selection checkboxes toggle correctly', () => {
    render(
      <SearchResults
        query="Z-transform"
        matches={[EXPLAINS_MATCH, USES_MATCH]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
      />
    )
    const checkboxes = screen.getAllByTestId('result-checkbox')
    expect(checkboxes).toHaveLength(2)

    // Initially unchecked
    expect(checkboxes[0]).not.toBeChecked()

    // Click to check
    fireEvent.click(checkboxes[0])
    expect(checkboxes[0]).toBeChecked()

    // Click again to uncheck
    fireEvent.click(checkboxes[0])
    expect(checkboxes[0]).not.toBeChecked()
  })

  it('Select All EXPLAINS selects only EXPLAINS matches', () => {
    render(
      <SearchResults
        query="Z-transform"
        matches={[EXPLAINS_MATCH, USES_MATCH]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
      />
    )
    fireEvent.click(screen.getByTestId('select-all-explains'))

    const checkboxes = screen.getAllByTestId('result-checkbox')
    // First match is EXPLAINS → should be checked
    expect(checkboxes[0]).toBeChecked()
    // Second match is USES → should NOT be checked
    expect(checkboxes[1]).not.toBeChecked()
  })

  it('shows empty state when no matches', () => {
    render(
      <SearchResults
        query="unknown concept"
        matches={[]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
      />
    )
    expect(screen.getByTestId('search-results-empty')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(
      <SearchResults
        query="Z-transform"
        matches={[]}
        onGenerateExplanation={vi.fn()}
        onGeneratePractice={vi.fn()}
        loading
      />
    )
    expect(screen.getByTestId('search-results-loading')).toBeInTheDocument()
  })
})
