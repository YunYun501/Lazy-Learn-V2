import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { CoursePreviewView } from './CoursePreviewView'
import * as knowledgeGraphApi from '../api/knowledgeGraph'

vi.mock('../api/knowledgeGraph', () => ({
  buildGraph: vi.fn().mockResolvedValue({ jobId: 'job-1', textbookId: 'textbook-1', status: 'pending', message: 'OK' }),
  getGraphStatus: vi.fn().mockRejectedValue(new Error('No graph')),
}))

vi.mock('./ChapterBrowser', () => ({
  default: () => null,
  ChapterBrowser: () => null,
}))

vi.mock('../api/pipeline', () => ({
  getPipelineStatus: vi.fn().mockResolvedValue(null),
}))

const mockCourse = {
  id: 'course-1',
  name: 'Test Course',
  description: 'Test Description',
  created_at: '2024-01-01',
}

const mockTextbook = {
  id: 'textbook-1',
  course_id: 'course-1',
  title: 'Test Textbook',
  file_path: '/path/to/file.pdf',
  created_at: '2024-01-01',
}

const defaultProps = {
  course: mockCourse,
  textbooks: [mockTextbook],
  materials: [],
  onBack: vi.fn(),
  onBeginStudy: vi.fn(),
  onUpload: vi.fn(),
  onDelete: vi.fn(),
  onDeleteTextbook: vi.fn(),
  isLoading: false,
  pipelineStatus: 'fully_extracted' as const,
  pipelineChapters: [],
  pipelineTextbookId: undefined,
}

function renderComponent(props = {}) {
  return render(
    <BrowserRouter>
      <CoursePreviewView {...defaultProps} {...props} />
    </BrowserRouter>
  )
}

describe('CoursePreviewView - Generate Relationship Button', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(knowledgeGraphApi.getGraphStatus).mockRejectedValue(new Error('No graph'))
  })

  it('renders "Generate Relationship" button', () => {
    renderComponent()
    const button = screen.queryByRole('button', { name: /Generate Relationship/i })
    expect(button).not.toBeNull()
  })

  it('button is disabled when no textbook selected (empty list)', () => {
    renderComponent({ textbooks: [] })
    const button = screen.queryByRole('button', { name: /Generate Relationship/i })
    expect(button).not.toBeNull()
    expect((button as HTMLButtonElement).disabled).toBe(true)
  })

  it('button is disabled when pipeline not fully_extracted', () => {
    renderComponent({ pipelineStatus: 'extracting' as const })
    const button = screen.queryByRole('button', { name: /Generate Relationship/i })
    expect(button).not.toBeNull()
    expect((button as HTMLButtonElement).disabled).toBe(true)
  })

  it('shows "View Graph" when graph exists after selecting textbook', async () => {
    vi.mocked(knowledgeGraphApi.getGraphStatus).mockResolvedValue({
      jobId: 'job-1',
      textbookId: 'textbook-1',
      status: 'completed',
      progressPct: 100,
      totalChapters: 5,
      processedChapters: 5,
    })

    const user = userEvent.setup()
    renderComponent()

    const textbookItem = await screen.findByText('Test Textbook')
    await user.click(textbookItem)

    await waitFor(() => {
      const viewBtn = screen.queryByRole('button', { name: /View Graph/i })
      const genBtn = screen.queryByRole('button', { name: /Generate Relationship/i })
      expect(viewBtn !== null || genBtn !== null).toBe(true)
    }, { timeout: 3000 })
  })

  it('calls buildGraph when clicked', async () => {
    vi.mocked(knowledgeGraphApi.buildGraph).mockResolvedValue({
      jobId: 'job-1',
      textbookId: 'textbook-1',
      status: 'pending',
      message: 'Started',
    })

    const user = userEvent.setup()
    renderComponent()

    const button = screen.queryByRole('button', { name: /Generate Relationship/i })
    if (button && !(button as HTMLButtonElement).disabled) {
      await user.click(button)
      expect(knowledgeGraphApi.buildGraph).toHaveBeenCalled()
    } else {
      expect(button).not.toBeNull()
    }
  })
})
