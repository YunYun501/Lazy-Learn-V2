import '@testing-library/jest-dom'
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'

describe('KaTeX', () => {
  it('renders LaTeX equation without throwing', () => {
    expect(() => render(<InlineMath math="E = mc^2" />)).not.toThrow()
  })

  it('renders equation container', () => {
    const { container } = render(<InlineMath math="E = mc^2" />)
    expect(container.querySelector('.katex')).toBeTruthy()
  })
})
