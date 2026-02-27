import React, { useState, useEffect, useRef } from 'react'
import { ContentRenderer } from './ContentRenderer'
import { PixelButton } from './pixel'
import type { ChapterRef } from '../api/search'
import '../styles/desk.css'

interface ExplanationViewProps {
  /** Chapters to explain */
  chapters: ChapterRef[]
  /** The user's query */
  query: string
  /** Called when user clicks a source citation */
  onSourceClick?: (source: string) => void
  /** Called when user clicks "Generate Practice" */
  onGeneratePractice?: () => void
  className?: string
}

type StreamState = 'idle' | 'loading' | 'streaming' | 'complete' | 'error'

/**
 * Streams an AI explanation from the backend SSE endpoint and renders it
 * progressively using ContentRenderer (Markdown + KaTeX).
 */
export function ExplanationView({
  chapters,
  query,
  onSourceClick,
  onGeneratePractice,
  className = '',
}: ExplanationViewProps) {
  const [content, setContent] = useState('')
  const [state, setState] = useState<StreamState>('idle')
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (chapters.length === 0 || !query) return

    // Abort any previous stream
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setContent('')
    setError(null)
    setState('loading')

    const run = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/api/explain', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chapters, query }),
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Server error: ${response.statusText}`)
        }

        if (!response.body) {
          throw new Error('No response body')
        }

        setState('streaming')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const chunk = line.slice(6)
              if (chunk === '[DONE]') {
                setState('complete')
                return
              }
              setContent((prev) => prev + chunk)
            }
          }
        }

        setState('complete')
      } catch (err) {
        if ((err as Error).name === 'AbortError') return
        setError((err as Error).message)
        setState('error')
      }
    }

    run()

    return () => {
      controller.abort()
    }
  }, [chapters, query])

  return (
    <div
      className={`explanation-view ${className}`}
      data-testid="explanation-view"
    >
      {state === 'loading' && (
        <div className="explanation-view__loading" data-testid="explanation-loading">
          <span className="explanation-view__cursor">Thinking...</span>
        </div>
      )}

      {(state === 'streaming' || state === 'complete') && content && (
        <div className="explanation-view__content" data-testid="explanation-content">
          <ContentRenderer
            content={content}
            onSourceClick={onSourceClick}
          />
          {state === 'streaming' && (
            <span
              className="explanation-view__cursor explanation-view__cursor--blink"
              data-testid="streaming-cursor"
              aria-label="streaming"
            >
              ▌
            </span>
          )}
        </div>
      )}

      {state === 'error' && (
        <div className="explanation-view__error" data-testid="explanation-error">
          <p>Error: {error}</p>
        </div>
      )}

      {state === 'complete' && onGeneratePractice && (
        <div className="explanation-view__actions" data-testid="explanation-actions">
          <PixelButton onClick={onGeneratePractice} variant="secondary">
            Generate Practice Problems
          </PixelButton>
        </div>
      )}
    </div>
  )
}

export default ExplanationView
