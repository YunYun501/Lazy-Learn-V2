import React, { useState, useEffect, useCallback } from 'react'
import { PixelButton } from './pixel'
import { getMaterialTopics, rescanMaterial, checkMaterialRelevance, getMaterialRelevance } from '../api/universityMaterials'
import type { MaterialTopic } from '../api/universityMaterials'
import type { MaterialRelevanceEntry } from '../types/pipeline'
import '../styles/bookshelf.css'

interface MaterialBrowserProps {
  materialId: string | null
  courseId: string | null
}

function getRelevanceBadge(score: number): { label: string; className: string } {
  if (score > 0.7) return { label: 'High', className: 'high' }
  if (score >= 0.4) return { label: 'Medium', className: 'medium' }
  return { label: 'Low', className: 'low' }
}

export function MaterialBrowser({ materialId }: MaterialBrowserProps) {
  const [topics, setTopics] = useState<MaterialTopic[]>([])
  const [rawSummary, setRawSummary] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [rescanning, setRescanning] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())
  const [relevanceResults, setRelevanceResults] = useState<MaterialRelevanceEntry[]>([])
  const [relevanceStatus, setRelevanceStatus] = useState<'none' | 'checking' | 'completed' | 'error'>('none')
  const [relevanceChecking, setRelevanceChecking] = useState(false)

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

  const fetchRelevance = useCallback(async () => {
    if (!materialId) return
    try {
      const data = await getMaterialRelevance(materialId)
      setRelevanceStatus(data.status)
      setRelevanceResults(data.results)
    } catch {
      // silently ignore
    }
  }, [materialId])

  useEffect(() => {
    setTopics([])
    setRawSummary(null)
    setExpandedIds(new Set())
    setRescanning(false)
    setRelevanceResults([])
    setRelevanceStatus('none')
    setRelevanceChecking(false)
    fetchTopics()
    fetchRelevance()
  }, [materialId, fetchTopics, fetchRelevance])

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
    }
  }, [materialId, rescanning, fetchTopics])

  const handleCheckRelevance = useCallback(async () => {
    if (!materialId || relevanceChecking) return
    setRelevanceChecking(true)
    setRelevanceStatus('checking')
    try {
      await checkMaterialRelevance(materialId)
      const poll = async () => {
        try {
          const data = await getMaterialRelevance(materialId)
          setRelevanceStatus(data.status)
          if (data.results && data.results.length > 0) {
            setRelevanceResults(data.results)
          }
          if (data.status === 'completed' || data.status === 'error') {
            setRelevanceChecking(false)
            clearInterval(pollInterval)
          }
        } catch {
          clearInterval(pollInterval)
          setRelevanceChecking(false)
          setRelevanceStatus('error')
        }
      }
      const pollInterval = setInterval(poll, 1500)
      setTimeout(() => poll(), 500)
      // Safety timeout — stop polling after 2 minutes
      setTimeout(() => {
        clearInterval(pollInterval)
        setRelevanceChecking(false)
      }, 120000)
    } catch {
      console.warn('MaterialBrowser: relevance check failed')
      setRelevanceChecking(false)
      setRelevanceStatus('error')
    }
  }, [materialId, relevanceChecking])

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

      {/* Relevant Chapters section */}
      {relevanceResults.length > 0 && (
        <div className="material-relevance-section">
          <div className="material-relevance-header">Relevant Chapters</div>
          <div className="material-relevance-list">
            {relevanceResults
              .sort((a, b) => b.relevance_score - a.relevance_score)
              .map((entry) => {
                const badge = getRelevanceBadge(entry.relevance_score)
                const indent = (entry.entry_level - 1) * 12
                return (
                  <div
                    key={entry.id}
                    className={`material-relevance-item level-${entry.entry_level}`}
                    style={{ paddingLeft: `${8 + indent}px` }}
                  >
                    <span className="material-relevance-title">{entry.entry_title}</span>
                    <div className="material-relevance-right">
                      <span className="material-relevance-pages">
                        pages {entry.page_start}–{entry.page_end}
                      </span>
                      <span className={`chapter-relevance-badge ${badge.className}`}>
                        {badge.label}
                      </span>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>
      )}

      <div className="material-browser-footer">
        {/* Progress bar during checking */}
        {relevanceChecking && (
          <div className="relevance-progress-container">
            <div className="relevance-progress-bar">
              <div className="relevance-progress-fill" />
            </div>
            <span className="relevance-progress-text">Checking relevance...</span>
          </div>
        )}
        <PixelButton
          variant="secondary"
          onClick={handleCheckRelevance}
          disabled={relevanceChecking}
        >
          {relevanceChecking ? 'Checking...' : 'Check Relevance'}
        </PixelButton>
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
