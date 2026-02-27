import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { DeskPage } from '../pages/DeskPage'

function renderDesk(textbookId = 'tb_001') {
  return render(
    <MemoryRouter initialEntries={[`/desk/${textbookId}`]}>
      <Routes>
        <Route path="/desk/:textbookId" element={<DeskPage />} />
        <Route path="/" element={<div data-testid="bookshelf">Bookshelf</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('DeskPage', () => {
  it('renders four-column layout', () => {
    renderDesk()
    expect(screen.getByTestId('input-column')).toBeInTheDocument()
    expect(screen.getByTestId('panel-a')).toBeInTheDocument()
    expect(screen.getByTestId('panel-b')).toBeInTheDocument()
    expect(screen.getByTestId('quick-ref')).toBeInTheDocument()
  })

  it('renders panel swap button', () => {
    renderDesk()
    expect(screen.getByText('⇄ SWAP')).toBeInTheDocument()
  })

  it('renders Generate Q&A button', () => {
    renderDesk()
    expect(screen.getByText('GENERATE Q&A')).toBeInTheDocument()
  })

  it('ESC key navigates back to bookshelf', () => {
    renderDesk()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.getByTestId('bookshelf')).toBeInTheDocument()
  })

  it('panel swap button is clickable', () => {
    renderDesk()
    const swapBtn = screen.getByText('⇄ SWAP')
    // Should not throw
    fireEvent.click(swapBtn)
    expect(swapBtn).toBeInTheDocument()
  })
})
