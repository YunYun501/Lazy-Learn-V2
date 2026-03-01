import '@testing-library/jest-dom'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { CoursePreviewView } from '../components/CoursePreviewView'
import type { Course } from '../api/courses'
import type { Textbook } from '../api/textbooks'
import type { UniversityMaterial } from '../api/universityMaterials'

// ── Mock data ────────────────────────────────────────────────────────────

const mockCourse: Course = {
  id: 'course-1',
  name: 'MECH0089',
  textbook_count: 2,
  created_at: '2026-01-01T00:00:00',
  material_count: 1,
}

const mockTextbooks: Textbook[] = [
  {
    id: 'tb-1',
    title: 'Control Systems',
    course: null,
    course_id: 'course-1',
    library_type: 'course',
    filepath: '/data/tb-1/original.pdf',
    processed_at: null,
  },
  {
    id: 'tb-2',
    title: 'Thermodynamics',
    course: null,
    course_id: 'course-1',
    library_type: 'course',
    filepath: '/data/tb-2/original.pdf',
    processed_at: null,
  },
]

const mockMaterials: UniversityMaterial[] = [
  {
    id: 'mat-1',
    course_id: 'course-1',
    title: 'Lecture Notes',
    file_type: 'pdf',
    filepath: '/data/mat-1.pdf',
    created_at: '2026-01-01T00:00:00',
  },
  {
    id: 'mat-2',
    course_id: 'course-1',
    title: 'Problem Set',
    file_type: 'pdf',
    filepath: '/data/mat-2.pdf',
    created_at: '2026-01-02T00:00:00',
  },
]

// ── Render helper ────────────────────────────────────────────────────────

function renderCoursePreview(
  course: Course = mockCourse,
  textbooks: Textbook[] = mockTextbooks,
  materials: UniversityMaterial[] = mockMaterials,
  onBack: () => void = vi.fn(),
  onBeginStudy: (textbookId: string) => void = vi.fn(),
  onUpload: () => void = vi.fn(),
  onDelete: () => void = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <Routes>
        <Route
          path="/"
          element={
            <CoursePreviewView
              course={course}
              textbooks={textbooks}
              materials={materials}
              onBack={onBack}
              onBeginStudy={onBeginStudy}
              onUpload={onUpload}
              onDelete={onDelete}
            />
          }
        />
        <Route path="/desk/:textbookId" element={<div data-testid="desk-page">Desk</div>} />
      </Routes>
    </MemoryRouter>
  )
}

// ── Test suite ──────────────────────────────────────────────────────────

describe('CoursePreviewView', () => {
  it('test_renders_textbook_list', async () => {
    renderCoursePreview()
    expect(await screen.findByText('Control Systems')).toBeInTheDocument()
    expect(screen.getByText('Thermodynamics')).toBeInTheDocument()
  })

  it('test_renders_materials_list', async () => {
    renderCoursePreview()
    expect(await screen.findByText('Lecture Notes')).toBeInTheDocument()
    expect(screen.getByText('Problem Set')).toBeInTheDocument()
  })

  it('test_renders_chapter_browser_panel', async () => {
    renderCoursePreview()
    expect(await screen.findByText('Chapters')).toBeInTheDocument()
    expect(screen.getByText('Select a textbook to browse chapters')).toBeInTheDocument()
  })

  it('test_back_button_calls_handler', async () => {
    const onBack = vi.fn()
    renderCoursePreview(mockCourse, mockTextbooks, mockMaterials, onBack)
    await screen.findByText('Control Systems')
    fireEvent.click(screen.getByText('← Back'))
    expect(onBack).toHaveBeenCalled()
  })

  it('test_begin_study_navigates', async () => {
    const onBeginStudy = vi.fn()
    renderCoursePreview(mockCourse, mockTextbooks, mockMaterials, vi.fn(), onBeginStudy)
    await screen.findByText('Control Systems')
    fireEvent.click(screen.getByText('Control Systems'))
    fireEvent.click(screen.getByRole('button', { name: 'Begin Study' }))
    expect(onBeginStudy).toHaveBeenCalledWith('tb-1')
  })
})
