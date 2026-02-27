import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import SplashScreen from '../components/SplashScreen'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('SplashScreen', () => {
  it('renders "Lazy Learn" title', () => {
    // Fetch never resolves — keeps the splash visible
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {}))

    render(<SplashScreen onReady={() => {}} />)

    expect(screen.getByText(/Lazy Learn/i)).toBeInTheDocument()
  })

  it('renders the loading subtitle', () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {}))

    render(<SplashScreen onReady={() => {}} />)

    // The text is split across multiple spans (the dots), so use partial match
    expect(screen.getByText(/Loading study assistant/i)).toBeInTheDocument()
  })

  it('calls onReady when health check returns 200', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 })

    const onReady = vi.fn()
    render(<SplashScreen onReady={onReady} />)

    await waitFor(() => {
      expect(onReady).toHaveBeenCalledOnce()
    })
  })

  it('keeps polling and eventually calls onReady when backend recovers', async () => {
    let callCount = 0
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++
      // Fail first two attempts, succeed on third
      if (callCount < 3) {
        return Promise.reject(new Error('ECONNREFUSED'))
      }
      return Promise.resolve({ ok: true, status: 200 })
    })

    const onReady = vi.fn()
    render(<SplashScreen onReady={onReady} />)

    // With 500ms interval and immediate first check, third call happens by ~1000ms
    await waitFor(
      () => {
        expect(onReady).toHaveBeenCalledOnce()
      },
      { timeout: 3000 },
    )
  })

  it('renders loading bar progressbar', () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {}))

    render(<SplashScreen onReady={() => {}} />)

    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })
})
