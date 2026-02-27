import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders the bookshelf page at root route', () => {
    render(<App />)
    // BookshelfPage renders "LAZY LEARN" title
    expect(screen.getByText('LAZY LEARN')).toBeInTheDocument()
  })
})
