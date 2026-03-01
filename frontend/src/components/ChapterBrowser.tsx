import React, { useState, useEffect, useCallback } from 'react'
import { PixelButton } from './pixel'
import { getTextbookStatus, getChapterSections, getSectionSubsections, extractDeferred } from '../api/pipeline'
import type { ChapterWithStatus } from '../types/pipeline'
import type { Section } from '../api/pipeline'
import '../styles/bookshelf.css'

interface ChapterBrowserProps {
  textbookId: string | null
}

export function ChapterBrowser({ textbookId }: ChapterBrowserProps) {
  const [chapters, setChapters] = useState<ChapterWithStatus[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [sectionsCache, setSectionsCache] = useState<Record<string, Section[]>>({})
  const [sectionsLoading, setSectionsLoading] = useState<Set<string>>(new Set())
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [expandedSectionIds, setExpandedSectionIds] = useState<Set<string>>(new Set())
  const [subsectionsCache, setSubsectionsCache] = useState<Record<string, Section[]>>({})
  const [subsectionsLoading, setSubsectionsLoading] = useState<Set<string>>(new Set())

  const fetchChapters = useCallback(async () => {
    if (!textbookId) return
    setLoading(true)
    try {
      const data = await getTextbookStatus(textbookId)
      setChapters(data.chapters)
    } catch {
      // silently ignore
    } finally {
      setLoading(false)
    }
  }, [textbookId])

  useEffect(() => {
    setChapters([])
    setExpandedIds(new Set())
    setSectionsCache({})
    setSelectedIds(new Set())
    setExpandedSectionIds(new Set())
    setSubsectionsCache({})
    setSubsectionsLoading(new Set())
    fetchChapters()
  }, [textbookId, fetchChapters])

  const toggleExpand = useCallback(async (chapterId: string) => {
    if (!textbookId) return
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(chapterId)) {
        next.delete(chapterId)
      } else {
        next.add(chapterId)
      }
      return next
    })
    // Lazy-fetch sections on first expand
    if (!sectionsCache[chapterId]) {
      setSectionsLoading(prev => new Set(prev).add(chapterId))
      try {
        const sections = await getChapterSections(textbookId, chapterId)
        setSectionsCache(prev => ({ ...prev, [chapterId]: sections }))
      } catch {
        setSectionsCache(prev => ({ ...prev, [chapterId]: [] }))
      } finally {
        setSectionsLoading(prev => {
          const next = new Set(prev)
          next.delete(chapterId)
          return next
        })
      }
    }
  }, [textbookId, sectionsCache])

  const handleChapterClick = useCallback((e: React.MouseEvent, chapterId: string) => {
    if (e.shiftKey) {
      setSelectedIds(prev => {
        const next = new Set(prev)
        if (next.has(chapterId)) {
          next.delete(chapterId)
        } else {
          next.add(chapterId)
        }
        return next
      })
    } else {
      toggleExpand(chapterId)
    }
  }, [toggleExpand])

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const handleExtractSelected = useCallback(async () => {
    if (!textbookId || selectedIds.size === 0) return
    try {
      await extractDeferred(textbookId, Array.from(selectedIds))
      setSelectedIds(new Set())
      setTimeout(() => { fetchChapters() }, 2000)
    } catch {
      // silently ignore
    }
  }, [textbookId, selectedIds, fetchChapters])

  const handleExtractAll = useCallback(async () => {
    if (!textbookId) return
    const unextracted = chapters
      .filter(ch => ch.extraction_status !== 'extracted')
      .map(ch => ch.id)
    if (unextracted.length === 0) return
    try {
      await extractDeferred(textbookId, unextracted)
      setTimeout(() => { fetchChapters() }, 2000)
    } catch {
      // silently ignore
    }
  }, [textbookId, chapters, fetchChapters])

  const handleExtractOne = useCallback(async (chapterId: string) => {
    if (!textbookId) return
    try {
      await extractDeferred(textbookId, [chapterId])
      setTimeout(() => { fetchChapters() }, 2000)
    } catch {
      // silently ignore
    }
  }, [textbookId, fetchChapters])

  const toggleSectionExpand = useCallback(async (sectionId: string) => {
    if (!textbookId) return
    setExpandedSectionIds(prev => {
      const next = new Set(prev)
      if (next.has(sectionId)) {
        next.delete(sectionId)
      } else {
        next.add(sectionId)
      }
      return next
    })
    if (!subsectionsCache[sectionId]) {
      setSubsectionsLoading(prev => new Set(prev).add(sectionId))
      try {
        const subs = await getSectionSubsections(textbookId, sectionId)
        setSubsectionsCache(prev => ({ ...prev, [sectionId]: subs }))
      } catch {
        setSubsectionsCache(prev => ({ ...prev, [sectionId]: [] }))
      } finally {
        setSubsectionsLoading(prev => {
          const next = new Set(prev)
          next.delete(sectionId)
          return next
        })
      }
    }
  }, [textbookId, subsectionsCache])

  if (!textbookId) {
    return (
      <p className="chapter-browser-empty">Select a textbook to browse chapters</p>
    )
  }

  if (loading) {
    return (
      <p className="chapter-browser-empty">Loading...</p>
    )
  }

  const unextractedCount = chapters.filter(ch => ch.extraction_status !== 'extracted').length

  return (
    <div className="chapter-browser">
      <div className="chapter-browser-list">
        {chapters.map(ch => {
          const isExpanded = expandedIds.has(ch.id)
          const isSelected = selectedIds.has(ch.id)
          const isExtracted = ch.extraction_status === 'extracted'
          const sections = sectionsCache[ch.id] ?? []
          const loadingSections = sectionsLoading.has(ch.id)

          return (
            <div key={ch.id}>
              <div
                className={`chapter-row${isSelected ? ' selected' : ''}`}
                onClick={(e) => { handleChapterClick(e, ch.id) }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    toggleExpand(ch.id)
                  }
                }}
              >
                <div className="chapter-row-left">
                  <span className="chapter-row-arrow">{isExpanded ? '\u25bc' : '\u25b6'}</span>
                  <span className="chapter-row-title">{ch.title}</span>
                </div>
                <div className="chapter-row-right">
                  {!isExtracted && ch.extraction_status !== 'extracting' && (
                    <button
                      className="chapter-extract-btn"
                      title="Extract this chapter"
                      onClick={(e) => { e.stopPropagation(); handleExtractOne(ch.id) }}
                    >{'\u2b07'}</button>
                  )}
                  {ch.extraction_status === 'extracting' && (
                    <span className="chapter-extract-btn" style={{ cursor: 'default' }}>{'\u23f3'}</span>
                  )}
                  <span
                    className={`chapter-status-dot${isExtracted ? ' extracted' : ' not-extracted'}`}
                    title={ch.extraction_status}
                  />
                </div>
              </div>

              {isExpanded && (
                <div className="chapter-sections">
                  {loadingSections && (
                    <div className="chapter-section-row">Loading sections...</div>
                  )}
                  {!loadingSections && sections.length === 0 && (
                    <div className="chapter-section-row">No sections found</div>
                  )}
                  {!loadingSections && sections.map(sec => {
                    const isSectionExpanded = expandedSectionIds.has(sec.id)
                    const loadingSubsections = subsectionsLoading.has(sec.id)
                    const subsections = subsectionsCache[sec.id] ?? []
                    return (
                      <div key={sec.id}>
                        <div
                          className="chapter-section-row expandable"
                          onClick={() => toggleSectionExpand(sec.id)}
                          role="button"
                          tabIndex={0}
                        >
                          <div className="section-row-left">
                            <span className="section-row-arrow">{isSectionExpanded ? '\u25bc' : '\u25b6'}</span>
                            <span className="chapter-section-title">{sec.title}</span>
                          </div>
                          <span className="chapter-section-pages">pp.{sec.page_start}{'\u2013'}{sec.page_end}</span>
                        </div>
                        {isSectionExpanded && (
                          <div className="chapter-subsections">
                            {loadingSubsections ? (
                              <div className="chapter-subsection-row">Loading...</div>
                            ) : subsections.length === 0 ? (
                              <div className="chapter-subsection-row">No sub-sections</div>
                            ) : (
                              subsections.map(sub => (
                                <div key={sub.id} className="chapter-subsection-row">
                                  <span className="chapter-subsection-title">{sub.title}</span>
                                  <span className="chapter-subsection-pages">pp.{sub.page_start}{'\u2013'}{sub.page_end}</span>
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="chapter-browser-footer">
        {selectedIds.size > 0 && (
          <div className="chapter-selection-info">
            <span>{selectedIds.size} selected</span>
            <button onClick={clearSelection}>clear</button>
          </div>
        )}

        {selectedIds.size > 0 && (
          <PixelButton variant="primary" onClick={handleExtractSelected}>
            Extract Selected
          </PixelButton>
        )}

        {unextractedCount > 0 && (
          <PixelButton variant="secondary" onClick={handleExtractAll}>
            Extract All ({unextractedCount})
          </PixelButton>
        )}
      </div>
    </div>
  )
}
