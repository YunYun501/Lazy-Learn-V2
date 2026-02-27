import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SettingsPage } from '../pages/SettingsPage'
import * as settingsApi from '../api/settings'
import * as textbooksApi from '../api/textbooks'

// Mock the API modules
vi.mock('../api/settings', () => ({
  getSettings: vi.fn(),
  updateSetting: vi.fn(),
  testConnection: vi.fn(),
}))

vi.mock('../api/textbooks', () => ({
  getTextbooks: vi.fn(),
  importTextbook: vi.fn(),
  getImportStatus: vi.fn(),
}))

function renderSettings() {
  return render(
    <MemoryRouter initialEntries={['/settings']}>
      <Routes>
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/" element={<div data-testid="bookshelf">Bookshelf</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.mocked(settingsApi.getSettings).mockResolvedValue({})
    vi.mocked(settingsApi.updateSetting).mockResolvedValue({ success: true, key: 'download_folder' })
    vi.mocked(settingsApi.testConnection).mockResolvedValue({ success: true, message: 'OK' })
    vi.mocked(textbooksApi.getTextbooks).mockResolvedValue([])
  })

  it('renders "API KEYS" section heading', async () => {
    renderSettings()
    expect(screen.getByText('API KEYS')).toBeInTheDocument()
  })

  it('renders SETTINGS title in the header', () => {
    renderSettings()
    expect(screen.getByText('SETTINGS')).toBeInTheDocument()
  })

  it('renders download folder section', () => {
    renderSettings()
    expect(screen.getByText('DOWNLOAD FOLDER')).toBeInTheDocument()
  })

  it('renders courses section', () => {
    renderSettings()
    expect(screen.getByText('COURSES')).toBeInTheDocument()
  })

  it('ESC key navigates back to bookshelf', () => {
    renderSettings()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.getByTestId('bookshelf')).toBeInTheDocument()
  })

  it('close button navigates back to bookshelf', () => {
    renderSettings()
    const closeBtn = screen.getByLabelText('Close settings')
    fireEvent.click(closeBtn)
    expect(screen.getByTestId('bookshelf')).toBeInTheDocument()
  })

  it('Save button calls updateSetting with download folder value', async () => {
    renderSettings()
    // Wait for page to fully render
    await screen.findByText('API KEYS')

    // Type into download folder input
    const folderInput = screen.getByTestId('download-folder-input')
    fireEvent.change(folderInput, { target: { value: '/my/data/path' } })

    // Click save
    const saveBtn = screen.getByTestId('save-btn').querySelector('button')!
    fireEvent.click(saveBtn)

    await waitFor(() => {
      expect(settingsApi.updateSetting).toHaveBeenCalledWith('download_folder', '/my/data/path')
    })
  })

  it('shows existing masked API key when settings are loaded', async () => {
    vi.mocked(settingsApi.getSettings).mockResolvedValue({
      deepseek_api_key: '****...d4c7',
    })
    renderSettings()
    const masked = await screen.findByText('****...d4c7')
    expect(masked).toBeInTheDocument()
  })

  it('renders courses list from textbooks API', async () => {
    vi.mocked(textbooksApi.getTextbooks).mockResolvedValue([
      {
        id: 'tb_001',
        title: 'Control Systems',
        filepath: '/data/tb_001/original.pdf',
        course: 'MECH0089',
        library_type: 'course',
        processed_at: null,
      },
    ])
    renderSettings()
    const course = await screen.findByText('MECH0089')
    expect(course).toBeInTheDocument()
  })

  it('Test button calls testConnection with deepseek provider', async () => {
    renderSettings()
    await screen.findByText('API KEYS')

    const testBtnContainer = screen.getByTestId('test-deepseek-btn')
    const testBtn = testBtnContainer.querySelector('button')!
    fireEvent.click(testBtn)

    await waitFor(() => {
      expect(settingsApi.testConnection).toHaveBeenCalledWith('deepseek')
    })
  })

  it('shows empty courses message when no courses exist', async () => {
    renderSettings()
    const msg = await screen.findByText(/No courses yet/i)
    expect(msg).toBeInTheDocument()
  })
})
