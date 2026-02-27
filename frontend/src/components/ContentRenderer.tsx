import React, { useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import '../styles/content-area.css'

interface ContentRendererProps {
  /** Markdown + LaTeX string to render */
  content: string
  /** Called when a source citation is clicked, e.g. [Source: Ch.3.2] */
  onSourceClick?: (source: string) => void
  /** Called when an equation is clicked for concept exploration */
  onEquationClick?: (equationLabel: string) => void
  className?: string
}

/**
 * Renders AI-generated Markdown + LaTeX content.
 *
 * Supports:
 * - Inline math: $E = mc^2$
 * - Display math: $$\frac{Y(z)}{X(z)} = \frac{az}{z-b}$$
 * - Warning disclaimers: > \u26a0\ufe0f **Warning**: ...
 * - Images with draggable attribute
 */
export function ContentRenderer({
  content,
  onSourceClick,
  onEquationClick,
  className = '',
}: ContentRendererProps) {
  // Detect if this content contains a warning (used by blockquote renderer)
  const contentHasWarning = content.includes('\u26a0\ufe0f') || content.toLowerCase().includes('> **warning')

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement
      const citation = target.closest('[data-source-citation]') as HTMLElement | null
      if (citation && onSourceClick) {
        onSourceClick(citation.dataset.sourceCitation ?? '')
        return
      }
      const equationEl = target.closest('.equation-wrapper') as HTMLElement | null
      if (equationEl && onEquationClick) {
        onEquationClick(equationEl.dataset.label ?? '')
      }
    },
    [onSourceClick, onEquationClick]
  )

  return (
    <div
      className={`content-renderer ${className}`}
      onClick={handleClick}
      data-testid="content-renderer"
    >
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          img: ({ src, alt, ...props }) => (
            <img
              src={src}
              alt={alt ?? ''}
              draggable
              className="content-image"
              data-testid="content-image"
              {...props}
            />
          ),
          // Blockquotes that contain warnings get special styling
          blockquote: ({ children, ...props }) => (
            <blockquote
              className={contentHasWarning ? 'content-warning' : 'content-blockquote'}
              data-testid={contentHasWarning ? 'warning-disclaimer' : 'blockquote'}
              {...props}
            >
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default ContentRenderer
