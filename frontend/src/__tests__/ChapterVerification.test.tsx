import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { ChapterVerification } from '../components/ChapterVerification'
import type { ChapterWithStatus } from '../types/pipeline'

// ── Mock data ────────────────────────────────────────────────────────────

const mockChapters: ChapterWithStatus[] = [
  {
    id: 'ch-1',
    title: 'Introduction to Control Systems',
    chapter_number: 1,
    page_start: 1,
    page_end: 30,
    extraction_status: 'pending',
    relevance_score: 0.9,
    matched_topics: ['control theory'],
  },
  {
    id: 'ch-2',
    title: 'Transfer Functions',
    chapter_number: 2,
    page_start: 31,
    page_end: 60,
    extraction_status: 'pending',
    relevance_score: 0.3,
  },
  {
    id: 'ch-3',
    title: 'State Space Representation',
    chapter_number: 3,
    page_start: 61,
    page_end: 90,
    extraction_status: 'pending',
  },
]

// ── Render helper ────────────────────────────────────────────────────────

function renderChapterVerification(
  chapters: ChapterWithStatus[] = mockChapters,
  onConfirm: (selectedIds: string[]) => void = vi.fn(),
  onBack: () => void = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <Routes>
        <Route
          path="/"
          element={
            <ChapterVerification
              chapters={chapters}
              onConfirm={onConfirm}
              onBack={onBack}
            />
          }
        />
      </Routes>
    </MemoryRouter>
  )
}

// ── Test suite ──────────────────────────────────────────────────────────

describe('ChapterVerification', () => {
  it('test_renders_chapter_list', async () => {
    renderChapterVerification()
    expect(await screen.findByText('Introduction to Control Systems')).toBeInTheDocument()
    expect(screen.getByText('Transfer Functions')).toBeInTheDocument()
    expect(screen.getByText('State Space Representation')).toBeInTheDocument()
  })

  it('test_chapters_toggleable', async () => {
    renderChapterVerification()
    // ch-1 has relevance_score 0.9 (> 0.5), so it's pre-checked
    const checkbox = await screen.findByRole('checkbox', { name: 'Introduction to Control Systems' })
    expect(checkbox).toBeChecked()
    fireEvent.click(checkbox)
    expect(checkbox).not.toBeChecked()
    // toggle back on
    fireEvent.click(checkbox)
    expect(checkbox).toBeChecked()
  })

  it('test_relevant_chapters_pre_selected', async () => {
    renderChapterVerification()
    // ch-1: score 0.9 (> 0.5) → pre-selected
    const ch1Checkbox = await screen.findByRole('checkbox', { name: 'Introduction to Control Systems' })
    expect(ch1Checkbox).toBeChecked()
    // ch-2: score 0.3 (not > 0.5) → NOT pre-selected
    const ch2Checkbox = screen.getByRole('checkbox', { name: 'Transfer Functions' })
    expect(ch2Checkbox).not.toBeChecked()
    // ch-3: no score → NOT pre-selected
    const ch3Checkbox = screen.getByRole('checkbox', { name: 'State Space Representation' })
    expect(ch3Checkbox).not.toBeChecked()
  })

  it('test_relevance_badge_shown', async () => {
    const badgeChapters: ChapterWithStatus[] = [
      { id: 'b-1', title: 'High Chapter', chapter_number: 1, page_start: 1, page_end: 10, extraction_status: 'pending', relevance_score: 0.8 },
      { id: 'b-2', title: 'Medium Chapter', chapter_number: 2, page_start: 11, page_end: 20, extraction_status: 'pending', relevance_score: 0.5 },
      { id: 'b-3', title: 'Low Chapter', chapter_number: 3, page_start: 21, page_end: 30, extraction_status: 'pending', relevance_score: 0.2 },
    ]
    renderChapterVerification(badgeChapters)
    expect(await screen.findByText('High')).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
    expect(screen.getByText('Low')).toBeInTheDocument()
  })

  it('test_confirm_sends_selected_ids', async () => {
    const onConfirm = vi.fn()
    renderChapterVerification(mockChapters, onConfirm)
    // ch-1 is pre-selected (score 0.9)
    await screen.findByText('Introduction to Control Systems')
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Selection' }))
    expect(onConfirm).toHaveBeenCalledWith(['ch-1'])
  })

  it('test_no_chapters_shows_empty_state', async () => {
    renderChapterVerification([])
    expect(await screen.findByText('No chapters found')).toBeInTheDocument()
  })

  it('test_escape_goes_back', async () => {
    const onBack = vi.fn()
    renderChapterVerification(mockChapters, vi.fn(), onBack)
    await screen.findByText('Introduction to Control Systems')
    fireEvent.keyDown(screen.getByTestId('chapter-verification'), { key: 'Escape' })
    expect(onBack).toHaveBeenCalled()
  })

  it('test_all_chapters_must_have_selection', async () => {
    const noPreSelectedChapters: ChapterWithStatus[] = [
      { id: 'np-1', title: 'Chapter One', chapter_number: 1, page_start: 1, page_end: 10, extraction_status: 'pending', relevance_score: 0.3 },
      { id: 'np-2', title: 'Chapter Two', chapter_number: 2, page_start: 11, page_end: 20, extraction_status: 'pending' },
    ]
    renderChapterVerification(noPreSelectedChapters)
    await screen.findByText('Chapter One')
    // None pre-selected → confirm button disabled
    expect(screen.getByRole('button', { name: 'Confirm Selection' })).toBeDisabled()
  })
})
