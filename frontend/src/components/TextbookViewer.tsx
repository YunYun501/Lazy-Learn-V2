import React, { useState, useEffect } from 'react'
import { ContentRenderer } from './ContentRenderer'
import { PixelButton } from './pixel'
import { getChapterContent } from '../api/chapters'
import type { ChapterContent } from '../api/chapters'
import '../styles/desk.css'

interface TextbookViewerProps {
  textbookId: string
  chapterNum: string
  /** Called when a source citation is clicked */
  onSourceClick?: (source: string) => void
  className?: string
}

/**
 * Displays the raw extracted text and images for a textbook chapter.
 * Triggered when user clicks a [Source: ...] citation in the explanation view.
 */
export function TextbookViewer({
  textbookId,
  chapterNum,
  onSourceClick,
  className = '',
}: TextbookViewerProps) {
  const [chapter, setChapter] = useState<ChapterContent | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentImageIdx, setCurrentImageIdx] = useState(0)

  useEffect(() => {
    if (!textbookId || !chapterNum) return

    setLoading(true)
    setError(null)
    setCurrentImageIdx(0)

    getChapterContent(textbookId, chapterNum)
      .then((data) => {
        setChapter(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [textbookId, chapterNum])

  if (loading) {
    return (
      <div className="textbook-viewer" data-testid="textbook-viewer-loading">
        <p>Loading chapter...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="textbook-viewer" data-testid="textbook-viewer-error">
        <p>Error: {error}</p>
      </div>
    )
  }

  if (!chapter) {
    return (
      <div className="textbook-viewer" data-testid="textbook-viewer-empty">
        <p>No chapter selected.</p>
      </div>
    )
  }

  const hasImages = chapter.image_urls.length > 0

  return (
    <div className={`textbook-viewer ${className}`} data-testid="textbook-viewer">
      <div className="textbook-viewer__header">
        <h3 className="textbook-viewer__title" data-testid="chapter-title">
          {chapter.title}
        </h3>
        <span className="textbook-viewer__pages">
          pp. {chapter.page_start}–{chapter.page_end}
        </span>
      </div>

      {hasImages && (
        <div className="textbook-viewer__images" data-testid="chapter-images">
          <img
            src={chapter.image_urls[currentImageIdx]}
            alt={`Figure ${currentImageIdx + 1}`}
            className="textbook-viewer__image"
            data-testid="chapter-image"
          />
          <div className="textbook-viewer__image-nav">
            <PixelButton
              onClick={() => setCurrentImageIdx((i) => Math.max(0, i - 1))}
              disabled={currentImageIdx === 0}
              variant="secondary"
            >
              ← Prev
            </PixelButton>
            <span data-testid="image-counter">
              {currentImageIdx + 1} / {chapter.image_urls.length}
            </span>
            <PixelButton
              onClick={() =>
                setCurrentImageIdx((i) =>
                  Math.min(chapter.image_urls.length - 1, i + 1)
                )
              }
              disabled={currentImageIdx === chapter.image_urls.length - 1}
              variant="secondary"
            >
              Next →
            </PixelButton>
          </div>
        </div>
      )}

      <div className="textbook-viewer__text" data-testid="chapter-text">
        <ContentRenderer
          content={chapter.text}
          onSourceClick={onSourceClick}
        />
      </div>
    </div>
  )
}

export default TextbookViewer
