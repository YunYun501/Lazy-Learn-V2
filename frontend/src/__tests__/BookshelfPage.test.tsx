import '@testing-library/jest-dom'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BookshelfPage } from '../pages/BookshelfPage'
import { getCourses, createCourse, deleteCourse } from '../api/courses'
import { getTextbooks, importTextbook, getImportStatus } from '../api/textbooks'
import { getUniversityMaterials, uploadUniversityMaterial } from '../api/universityMaterials'

// ── Mock all API modules ────────────────────────────────────────────────────

vi.mock('../api/courses', () => ({
  getCourses: vi.fn(),
  createCourse: vi.fn(),
  deleteCourse: vi.fn(),
}))

vi.mock('../api/textbooks', () => ({
  getTextbooks: vi.fn(),
  importTextbook: vi.fn(),
  getImportStatus: vi.fn(),
}))

vi.mock('../api/universityMaterials', () => ({
  getUniversityMaterials: vi.fn(),
  uploadUniversityMaterial: vi.fn(),
}))

// ── Default mock data ───────────────────────────────────────────────────────

const mockCourses = [
  { id: 'course-1', name: 'MECH0089', textbook_count: 2, created_at: '2026-01-01T00:00:00', material_count: 0 },
  { id: 'math-lib', name: 'Math Library', textbook_count: 5, created_at: '2026-01-01T00:00:00', material_count: 0 },
]

const mockTextbooks = [
  {
    id: 'tb-1',
    title: 'Control Systems',
    course: null,
    course_id: 'course-1',
    library_type: 'course',
    filepath: '/data/tb-1/original.pdf',
    processed_at: null,
  },
]

const mockMaterials = [
  {
    id: 'mat-1',
    course_id: 'course-1',
    title: 'Lecture Notes',
    file_type: 'pdf',
    filepath: '/data/mat-1.pdf',
    created_at: '2026-01-01T00:00:00',
  },
]

// ── Render helper ───────────────────────────────────────────────────────────

function renderBookshelf() {
  return render(
    <MemoryRouter>
      <BookshelfPage />
    </MemoryRouter>
  )
}

// ── Test suite ──────────────────────────────────────────────────────────────

describe('BookshelfPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getCourses).mockResolvedValue(mockCourses)
    vi.mocked(getTextbooks).mockResolvedValue(mockTextbooks)
    vi.mocked(getUniversityMaterials).mockResolvedValue(mockMaterials)
    vi.mocked(createCourse).mockResolvedValue({
      id: 'new-id',
      name: 'New Course',
      textbook_count: 0,
      created_at: '2026-01-01T00:00:00',
      material_count: 0,
    })
    vi.mocked(deleteCourse).mockResolvedValue(undefined)
    // importTextbook and uploadUniversityMaterial are not triggered in any test
    // but mocking prevents accidental network calls
    vi.mocked(importTextbook).mockResolvedValue({ textbook_id: 'tb-x', job_id: 'job-1', message: 'ok' })
    vi.mocked(getImportStatus).mockResolvedValue({ textbook_id: 'tb-x', status: 'complete', chapters_found: 1 })
    vi.mocked(uploadUniversityMaterial).mockResolvedValue({
      id: 'mat-x',
      course_id: 'course-1',
      title: 'File',
      file_type: 'pdf',
      filepath: '/data/mat-x.pdf',
      created_at: '2026-01-01T00:00:00',
    })
  })

  // ── Layout ────────────────────────────────────────────────────────────────

  it('renders 3-column bookshelf grid in home view', async () => {
    renderBookshelf()
    await waitFor(() =>
      expect(document.querySelector('.bookshelf-grid')).toBeInTheDocument()
    )
  })

  // ── Course loading ────────────────────────────────────────────────────────

  it('loads and displays courses from API', async () => {
    renderBookshelf()
    expect(await screen.findByText('MECH0089')).toBeInTheDocument()
    expect(screen.getByText('Math Library')).toBeInTheDocument()
  })

  it('shows Loading... while courses are fetching', () => {
    renderBookshelf()
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows "No courses found." when course list is empty', async () => {
    vi.mocked(getCourses).mockResolvedValue([])
    renderBookshelf()
    expect(await screen.findByText('No courses found.')).toBeInTheDocument()
  })

  // ── Search ────────────────────────────────────────────────────────────────

  it('search bar filters courses by name', async () => {
    renderBookshelf()
    await screen.findByText('MECH0089')
    fireEvent.change(screen.getByLabelText('Search courses'), { target: { value: 'MECH' } })
    expect(screen.getByText('MECH0089')).toBeInTheDocument()
    expect(screen.queryByText('Math Library')).not.toBeInTheDocument()
  })

  // ── Selection ─────────────────────────────────────────────────────────────

  it('clicking a course adds the selected class', async () => {
    renderBookshelf()
    const courseItem = await screen.findByTitle('MECH0089')
    fireEvent.click(courseItem)
    expect(courseItem).toHaveClass('selected')
  })

  it('double-clicking a course transitions to course-preview-view', async () => {
    renderBookshelf()
    const courseItem = await screen.findByTitle('MECH0089')
    fireEvent.doubleClick(courseItem)
    await waitFor(() =>
      expect(document.querySelector('.course-preview-view')).toBeInTheDocument()
    )
  })

  // ── Create course dialog ──────────────────────────────────────────────────

  it('clicking "+ New Course" opens the create course dialog', async () => {
    renderBookshelf()
    await screen.findByText('MECH0089')
    fireEvent.click(screen.getByText('+ New Course'))
    expect(screen.getByText('New Course')).toBeInTheDocument()
  })

  it('course creation calls createCourse API with typed name', async () => {
    renderBookshelf()
    await screen.findByText('MECH0089')
    fireEvent.click(screen.getByText('+ New Course'))
    fireEvent.change(screen.getByTestId('create-course-input'), { target: { value: 'Test Course' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(createCourse).toHaveBeenCalledWith('Test Course'))
  })

  it('submitting an empty course name shows a validation error', async () => {
    renderBookshelf()
    await screen.findByText('MECH0089')
    fireEvent.click(screen.getByText('+ New Course'))
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    expect(screen.getByText('Course name cannot be empty')).toBeInTheDocument()
  })

  // ── Math Library protection ───────────────────────────────────────────────

  it('Upload button is visible when a non-Math-Library course is selected', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    expect(screen.getByText('Upload')).toBeInTheDocument()
  })

  it('Upload button is NOT visible when Math Library is selected', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('Math Library'))
    expect(screen.queryByText('Upload')).not.toBeInTheDocument()
  })

  it('Delete button is visible when a non-Math-Library course is selected', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('Delete button is NOT visible when Math Library is selected', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('Math Library'))
    expect(screen.queryByText('Delete')).not.toBeInTheDocument()
  })

  // ── Upload dialog ─────────────────────────────────────────────────────────

  it('Upload dialog opens at choice step with two upload type buttons', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Upload'))
    expect(screen.getByText('Upload Content')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Textbook/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /University Material/i })).toBeInTheDocument()
  })

  it('selecting Textbook in upload dialog shows the PDF file input', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Upload'))
    fireEvent.click(screen.getByRole('button', { name: /Textbook/i }))
    expect(screen.getByTestId('textbook-file-input')).toBeInTheDocument()
  })

  it('selecting University Material in upload dialog shows the material file input', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Upload'))
    fireEvent.click(screen.getByRole('button', { name: /University Material/i }))
    expect(screen.getByTestId('material-file-input')).toBeInTheDocument()
  })

  // ── Delete dialog ─────────────────────────────────────────────────────────

  it('Delete button opens the delete confirmation dialog', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Delete'))
    expect(screen.getByText('Delete Course')).toBeInTheDocument()
  })

  it('confirming delete calls deleteCourse API with the course id', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Delete'))
    const dialog = document.querySelector('.pixel-dialog') as HTMLElement
    fireEvent.click(within(dialog).getByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(deleteCourse).toHaveBeenCalledWith('course-1'))
  })

  it('canceling the delete dialog does not call deleteCourse', async () => {
    renderBookshelf()
    fireEvent.click(await screen.findByTitle('MECH0089'))
    fireEvent.click(screen.getByText('Delete'))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(deleteCourse).not.toHaveBeenCalled()
  })

  // ── Preview view ──────────────────────────────────────────────────────────

  it('preview view shows textbooks, materials, and tbd panels', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    await waitFor(() => {
      expect(document.querySelector('.textbooks-panel')).toBeInTheDocument()
      expect(document.querySelector('.materials-panel')).toBeInTheDocument()
      expect(document.querySelector('.tbd-panel')).toBeInTheDocument()
    })
  })

  it('textbooks panel renders textbook titles from API', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    expect(await screen.findByText('Control Systems')).toBeInTheDocument()
  })

  it('materials panel renders material titles from API', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    expect(await screen.findByText('Lecture Notes')).toBeInTheDocument()
  })

  it('Begin Study button is disabled when no textbook is selected', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    await screen.findByText('Control Systems')
    expect(screen.getByRole('button', { name: 'Begin Study' })).toBeDisabled()
  })

  // ── Navigation ────────────────────────────────────────────────────────────

  it('Back button in preview view returns to home view', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    await waitFor(() =>
      expect(document.querySelector('.course-preview-view')).toBeInTheDocument()
    )
    fireEvent.click(screen.getByText('← Back'))
    await waitFor(() =>
      expect(document.querySelector('.bookshelf-grid')).toBeInTheDocument()
    )
    expect(document.querySelector('.course-preview-view')).not.toBeInTheDocument()
  })

  it('Settings button navigates to /settings', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<BookshelfPage />} />
          <Route path="/settings" element={<div data-testid="settings-page">Settings</div>} />
        </Routes>
      </MemoryRouter>
    )
    await screen.findByText('MECH0089')
    fireEvent.click(screen.getByRole('button', { name: 'Settings' }))
    expect(await screen.findByTestId('settings-page')).toBeInTheDocument()
  })

  // ── Reserve space ─────────────────────────────────────────────────────────

  it('reserve space panel shows Coming Soon text', async () => {
    renderBookshelf()
    await screen.findByText('MECH0089')
    expect(screen.getByText('Coming Soon')).toBeInTheDocument()
  })

  // ── Keyboard navigation ───────────────────────────────────────────────────

  it('Enter key on a course item transitions to preview view', async () => {
    renderBookshelf()
    const courseItem = await screen.findByTitle('MECH0089')
    fireEvent.keyDown(courseItem, { key: 'Enter' })
    await waitFor(() =>
      expect(document.querySelector('.course-preview-view')).toBeInTheDocument()
    )
  })

  it('Space key on a course item selects it without entering preview', async () => {
    renderBookshelf()
    const courseItem = await screen.findByTitle('MECH0089')
    fireEvent.keyDown(courseItem, { key: ' ' })
    expect(courseItem).toHaveClass('selected')
    expect(document.querySelector('.course-preview-view')).not.toBeInTheDocument()
  })

  it('Escape key while in preview view returns to home view', async () => {
    renderBookshelf()
    fireEvent.doubleClick(await screen.findByTitle('MECH0089'))
    await waitFor(() =>
      expect(document.querySelector('.course-preview-view')).toBeInTheDocument()
    )
    fireEvent.keyDown(window, { key: 'Escape' })
    await waitFor(() =>
      expect(document.querySelector('.bookshelf-grid')).toBeInTheDocument()
    )
  })
})
