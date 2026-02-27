import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ContentRenderer } from '../components/ContentRenderer'

describe('ContentRenderer', () => {
  it('renders plain markdown text', () => {
    render(<ContentRenderer content="Hello **world**" />)
    expect(screen.getByTestId('content-renderer')).toBeInTheDocument()
    expect(screen.getByText('world')).toBeInTheDocument()
  })

  it('renders LaTeX inline math without error', () => {
    render(<ContentRenderer content="The equation $E = mc^2$ is famous." />)
    // KaTeX renders a .katex element
    const container = screen.getByTestId('content-renderer')
    expect(container).toBeInTheDocument()
    // Should not contain katex-error
    expect(container.querySelector('.katex-error')).toBeNull()
  })

  it('renders display math block without error', () => {
    render(<ContentRenderer content="$$Y(z) = \\frac{0.5z}{z - 0.8}$$" />)
    const container = screen.getByTestId('content-renderer')
    expect(container.querySelector('.katex-error')).toBeNull()
  })

  it('renders images with draggable attribute', () => {
    render(<ContentRenderer content="![test image](http://localhost:8000/api/textbooks/tb_001/images/test.png)" />)
    const img = screen.getByTestId('content-image')
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('draggable', 'true')
  })

  it('renders warning disclaimer with warning styling', () => {
    render(<ContentRenderer content="> ⚠️ **Warning**: AI-generated solutions may contain errors. Verify independently." />)
    const warning = screen.getByTestId('warning-disclaimer')
    expect(warning).toBeInTheDocument()
    expect(warning).toHaveClass('content-warning')
  })

  it('renders with onSourceClick handler without crashing', () => {
    const onSourceClick = vi.fn()
    render(
      <ContentRenderer
        content="See the reference for details."
        onSourceClick={onSourceClick}
      />
    )
    const container = screen.getByTestId('content-renderer')
    expect(container).toBeInTheDocument()
  })
})
