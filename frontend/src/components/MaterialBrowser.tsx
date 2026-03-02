import React, { useState, useEffect, useCallback } from 'react'
import { PixelButton } from './pixel'
import { getMaterialTopics, rescanMaterial } from '../api/universityMaterials'
import type { MaterialTopic } from '../api/universityMaterials'
import '../styles/bookshelf.css'

interface MaterialBrowserProps {
  materialId: string | null
}

export function MaterialBrowser({ materialId }: MaterialBrowserProps) {
  const [topics, setTopics] = useState<MaterialTopic[]>([])
  const [rawSummary, setRawSummary] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [rescanning, setRescanning] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  const fetchTopics = useCallback(async () => {
    if (!materialId) return
    setLoading(true)
    try {
      const data = await getMaterialTopics(materialId)
      setTopics(data.topics)
      setRawSummary(data.raw_summary)
    } catch (err) {
      console.warn('MaterialBrowser:', err)
      // silently ignore
    } finally {
      setLoading(false)
    }
  }, [materialId])

  useEffect(() => {
    setTopics([])
    setRawSummary(null)
    setExpandedIds(new Set())
    setRescanning(false)
    fetchTopics()
  }, [materialId, fetchTopics])

  const toggleExpand = useCallback((index: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }, [])

  const handleRescan = useCallback(async () => {
    if (!materialId || rescanning) return
    setRescanning(true)
    try {
      await rescanMaterial(materialId)
      setTimeout(() => {
        fetchTopics()
        setRescanning(false)
      }, 5000)
    } catch (err) {
      console.warn('MaterialBrowser:', err)
      setRescanning(false)
      setRescanning(false)
    }
  }, [materialId, rescanning, fetchTopics])

  if (!materialId) {
    return (
      <p className="material-browser-empty">Select a material to browse topics</p>
    )
  }

  if (loading) {
    return (
      <p className="material-browser-empty">Loading...</p>
    )
  }

  return (
    <div className="material-browser">
      <div className="material-browser-list">
        {topics.length === 0 && (
          <p className="material-browser-empty">No topics categorized yet</p>
        )}
        {topics.map((topic, index) => {
          const isExpanded = expandedIds.has(index)
          return (
            <div key={index}>
              <div
                className="material-topic-row"
                onClick={() => { toggleExpand(index) }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    toggleExpand(index)
                  }
                }}
              >
                <div className="material-topic-left">
                  <span className="material-topic-arrow">{isExpanded ? '\u25bc' : '\u25b6'}</span>
                  <span className="material-topic-title">{topic.title}</span>
                </div>
                <span className="material-topic-range">{topic.source_range}</span>
              </div>
              {isExpanded && topic.description && (
                <div className="material-topic-description">
                  {topic.description}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {rawSummary && (
        <div className="material-browser-summary">{rawSummary}</div>
      )}

      <div className="material-browser-footer">
        <PixelButton
          variant="secondary"
          onClick={handleRescan}
          disabled={rescanning}
        >
          {rescanning ? 'Rescanning...' : 'Rescan'}
        </PixelButton>
      </div>
    </div>
  )
}
