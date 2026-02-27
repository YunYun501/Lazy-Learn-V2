import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'

// Mock fetch so SplashScreen immediately signals backend ready,
// allowing the normal routing (BookshelfPage) to render.
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('renders the bookshelf page at root route', async () => {
    render(<App />)
    // SplashScreen transitions to BookshelfPage once the mocked health check succeeds
    await waitFor(() => {
      expect(screen.getByText('LAZY LEARN')).toBeInTheDocument()
    })
  })
})
