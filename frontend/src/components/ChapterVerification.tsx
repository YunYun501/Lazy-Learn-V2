import React, { useState } from 'react'
import { PixelButton, PixelPanel } from './pixel'
import type { ChapterWithStatus } from '../types/pipeline'
import '../styles/bookshelf.css'

export interface ChapterVerificationProps {
  chapters: ChapterWithStatus[]
  onConfirm: (selectedIds: string[]) => void
  onBack: () => void
}

function getRelevanceBadge(
  score: number | undefined
): { label: string; className: string } | null {
  if (score === undefined) return null
  if (score > 0.7) return { label: 'High', className: 'high' }
  if (score >= 0.4) return { label: 'Medium', className: 'medium' }
  return { label: 'Low', className: 'low' }
}

export function ChapterVerification({
  chapters,
  onConfirm,
  onBack,
}: ChapterVerificationProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(() =>
    chapters
      .filter(ch => (ch.relevance_score ?? 0) > 0.5)
      .map(ch => ch.id)
  )

  const toggleChapter = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') onBack()
  }

  return (
    <div
      className="chapter-verification"
      onKeyDown={handleKeyDown}
      tabIndex={0}
      data-testid="chapter-verification"
    >
      <PixelPanel className="chapter-verification-panel">
        <h3 className="panel-title">Select Chapters</h3>

        {chapters.length === 0 ? (
          <p className="panel-message">No chapters found</p>
        ) : (
          <div className="chapter-list preview-list">
            {chapters.map(ch => {
              const badge = getRelevanceBadge(ch.relevance_score)
              const isSelected = selectedIds.includes(ch.id)

              return (
                <div key={ch.id} className="chapter-item">
                  <input
                    type="checkbox"
                    id={`ch-${ch.id}`}
                    className="chapter-item-checkbox"
                    checked={isSelected}
                    onChange={() => toggleChapter(ch.id)}
                    aria-label={ch.title}
                  />
                  <label
                    htmlFor={`ch-${ch.id}`}
                    className="chapter-item-title"
                  >
                    {ch.title}
                  </label>
                  <span className="chapter-item-pages">
                    pages {ch.page_start}–{ch.page_end}
                  </span>
                  {badge !== null && (
                    <span className={`chapter-relevance-badge ${badge.className}`}>
                      {badge.label}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <div className="panel-footer chapter-verification-footer">
          <PixelButton variant="secondary" onClick={onBack}>
            ← Back
          </PixelButton>
          <PixelButton
            variant="primary"
            disabled={selectedIds.length === 0}
            onClick={() => onConfirm(selectedIds)}
          >
            Confirm Selection
          </PixelButton>
        </div>
      </PixelPanel>
    </div>
  )
}
