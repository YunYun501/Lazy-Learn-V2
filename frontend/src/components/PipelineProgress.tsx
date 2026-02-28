import React, { useState, useEffect } from 'react'
import { PixelButton, PixelPanel } from './pixel'
import { getExtractionProgress, extractDeferred } from '../api/pipeline'
import type { PipelineStatus, ExtractionStatus, ChapterWithStatus } from '../types/pipeline'
import '../styles/bookshelf.css'

export interface PipelineProgressProps {
  textbookId: string
  initialStatus: PipelineStatus
  chapters: ChapterWithStatus[]
}

function statusIcon(status: ExtractionStatus): string {
  switch (status) {
    case 'extracting': return '⏳'
    case 'extracted':  return '✓'
    case 'error':      return '✗'
    case 'deferred':   return '—'
    case 'selected':   return '○'
    case 'pending':    return '○'
    default:           return '?'
  }
}

function titleForStatus(pipelineStatus: PipelineStatus): string {
  switch (pipelineStatus) {
    case 'extracting':          return 'Extracting...'
    case 'fully_extracted':     return 'Extraction complete'
    case 'partially_extracted': return 'Partially extracted'
    case 'error':               return 'Extraction error'
    default:                    return 'Processing...'
  }
}

export function PipelineProgress({
  textbookId,
  initialStatus,
  chapters: initialChapters,
}: PipelineProgressProps) {
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>(initialStatus)
  const [chapters, setChapters] = useState<ChapterWithStatus[]>(initialChapters)

  // ── Poll for progress when actively extracting ─────────────────────────
  useEffect(() => {
    if (pipelineStatus !== 'extracting') return

    const interval = setInterval(async () => {
      try {
        const progress = await getExtractionProgress(textbookId)
        setChapters(progress.chapters)
        setPipelineStatus(progress.pipeline_status)
      } catch {
        // silently ignore network errors — keep polling
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [pipelineStatus, textbookId])

  // ── Derived state ──────────────────────────────────────────────────────
  const deferredChapters = chapters.filter(ch => ch.extraction_status === 'deferred')
  const extractedCount   = chapters.filter(ch => ch.extraction_status === 'extracted').length
  const isSettled =
    pipelineStatus === 'fully_extracted' || pipelineStatus === 'partially_extracted'

  // ── Handlers ───────────────────────────────────────────────────────────
  const handleExtractRemaining = async () => {
    const deferredIds = deferredChapters.map(ch => ch.id)
    await extractDeferred(textbookId, deferredIds)
    setPipelineStatus('extracting')
  }

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <PixelPanel className="pipeline-progress">
      <h3 className="pipeline-progress-title">{titleForStatus(pipelineStatus)}</h3>

      <div className="pipeline-chapter-list">
        {chapters.map(ch => (
          <div key={ch.id} className="pipeline-chapter-item">
            <span className={`pipeline-chapter-status ${ch.extraction_status}`}>
              {statusIcon(ch.extraction_status)}
            </span>
            <span className="pipeline-chapter-title">{ch.title}</span>
          </div>
        ))}
      </div>

      {isSettled && (
        <p className="pipeline-summary">
          {extractedCount} of {chapters.length} chapters extracted
        </p>
      )}

      {isSettled && deferredChapters.length > 0 && (
        <div className="pipeline-progress-footer">
          <PixelButton variant="primary" onClick={handleExtractRemaining}>
            Extract remaining chapters
          </PixelButton>
        </div>
      )}
    </PixelPanel>
  )
}
