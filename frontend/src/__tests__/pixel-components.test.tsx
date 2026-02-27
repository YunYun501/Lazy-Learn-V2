import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PixelButton, PixelPanel, PixelInput, PixelBadge, PixelDialog } from '../components/pixel'

describe('PixelButton', () => {
  it('renders with primary variant by default', () => {
    render(<PixelButton>Click me</PixelButton>)
    const btn = screen.getByRole('button', { name: 'Click me' })
    expect(btn).toBeInTheDocument()
    expect(btn.className).toContain('pixel-btn--primary')
  })

  it('renders secondary variant', () => {
    render(<PixelButton variant="secondary">Secondary</PixelButton>)
    const btn = screen.getByRole('button')
    expect(btn.className).toContain('pixel-btn--secondary')
  })

  it('calls onClick when clicked', () => {
    const onClick = vi.fn()
    render(<PixelButton onClick={onClick}>Click</PixelButton>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})

describe('PixelPanel', () => {
  it('renders children', () => {
    render(<PixelPanel><p>Content here</p></PixelPanel>)
    expect(screen.getByText('Content here')).toBeInTheDocument()
  })

  it('has pixel-panel class', () => {
    const { container } = render(<PixelPanel>Content</PixelPanel>)
    expect(container.firstChild).toHaveClass('pixel-panel')
  })
})

describe('PixelBadge', () => {
  it('renders EXPLAINS badge with correct class', () => {
    render(<PixelBadge type="EXPLAINS" />)
    const badge = screen.getByTestId('badge-EXPLAINS')
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain('pixel-badge--explains')
    expect(badge.textContent).toBe('EXPLAINS')
  })

  it('renders USES badge with correct class', () => {
    render(<PixelBadge type="USES" />)
    const badge = screen.getByTestId('badge-USES')
    expect(badge.className).toContain('pixel-badge--uses')
    expect(badge.textContent).toBe('USES')
  })
})

describe('PixelInput', () => {
  it('renders input and calls onChange', () => {
    const onChange = vi.fn()
    render(<PixelInput value="" onChange={onChange} placeholder="Type here" />)
    const input = screen.getByPlaceholderText('Type here')
    expect(input).toBeInTheDocument()
    fireEvent.change(input, { target: { value: 'Z-transform' } })
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ type: 'change' }))
  })
})

describe('PixelDialog', () => {
  it('renders when open', () => {
    render(
      <PixelDialog isOpen={true} onClose={() => {}} title="Test Dialog">
        <p>Dialog content</p>
      </PixelDialog>
    )
    expect(screen.getByText('Test Dialog')).toBeInTheDocument()
    expect(screen.getByText('Dialog content')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(
      <PixelDialog isOpen={false} onClose={() => {}} title="Hidden">
        <p>Hidden content</p>
      </PixelDialog>
    )
    expect(screen.queryByText('Hidden')).not.toBeInTheDocument()
  })

  it('calls onClose when ESC is pressed', () => {
    const onClose = vi.fn()
    render(
      <PixelDialog isOpen={true} onClose={onClose} title="ESC Test">
        <p>Content</p>
      </PixelDialog>
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })
})
