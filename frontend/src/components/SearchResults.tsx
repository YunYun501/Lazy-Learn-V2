import React, { useState } from 'react'
import { PixelBadge, PixelButton } from './pixel'
import type { CategorizedMatch } from '../api/search'
import '../styles/desk.css'

interface SearchResultsProps {
  query: string
  matches: CategorizedMatch[]
  onGenerateExplanation: (selected: CategorizedMatch[]) => void
  onGeneratePractice: (selected: CategorizedMatch[]) => void
  loading?: boolean
}

export function SearchResults({
  query,
  matches,
  onGenerateExplanation,
  onGeneratePractice,
  loading = false,
}: SearchResultsProps) {
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const explains = matches.filter((m) => m.classification === 'EXPLAINS')
  const uses = matches.filter((m) => m.classification === 'USES')

  const toggle = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const selectAllExplains = () => {
    const explainIndices = matches
      .map((m, i) => (m.classification === 'EXPLAINS' ? i : -1))
      .filter((i) => i >= 0)
    setSelected(new Set(explainIndices))
  }

  const selectedMatches = matches.filter((_, i) => selected.has(i))

  if (loading) {
    return (
      <div className="search-results" data-testid="search-results-loading">
        <p className="search-results__loading">Searching...</p>
      </div>
    )
  }

  if (matches.length === 0) {
    return (
      <div className="search-results" data-testid="search-results-empty">
        <p className="search-results__empty">No results found for "{query}"</p>
      </div>
    )
  }

  return (
    <div className="search-results" data-testid="search-results">
      <div className="search-results__header">
        <span className="search-results__count">
          {matches.length} result{matches.length !== 1 ? 's' : ''} for "{query}"
        </span>
        {explains.length > 0 && (
          <button
            className="search-results__select-all"
            onClick={selectAllExplains}
            data-testid="select-all-explains"
          >
            Select All EXPLAINS
          </button>
        )}
      </div>

      <div className="search-results__list">
        {/* EXPLAINS first */}
        {explains.length > 0 && (
          <div className="search-results__group">
            <h4 className="search-results__group-label">EXPLAINS</h4>
            {matches.map((match, idx) =>
              match.classification === 'EXPLAINS' ? (
                <SearchResultItem
                  key={idx}
                  match={match}
                  checked={selected.has(idx)}
                  onToggle={() => toggle(idx)}
                />
              ) : null
            )}
          </div>
        )}

        {/* USES second */}
        {uses.length > 0 && (
          <div className="search-results__group">
            <h4 className="search-results__group-label">USES</h4>
            {matches.map((match, idx) =>
              match.classification === 'USES' ? (
                <SearchResultItem
                  key={idx}
                  match={match}
                  checked={selected.has(idx)}
                  onToggle={() => toggle(idx)}
                />
              ) : null
            )}
          </div>
        )}
      </div>

      <div className="search-results__actions">
        <div data-testid="generate-explanation-btn">
          <PixelButton
            onClick={() => onGenerateExplanation(selectedMatches)}
            disabled={selectedMatches.length === 0}
          >
            Generate Explanation
          </PixelButton>
        </div>
        <div data-testid="generate-practice-btn">
          <PixelButton
            variant="secondary"
            onClick={() => onGeneratePractice(selectedMatches)}
            disabled={selectedMatches.length === 0}
          >
            Generate Practice
          </PixelButton>
        </div>
      </div>
    </div>
  )
}

interface SearchResultItemProps {
  match: CategorizedMatch
  checked: boolean
  onToggle: () => void
}

function SearchResultItem({ match, checked, onToggle }: SearchResultItemProps) {
  const confidencePct = Math.round(match.confidence * 100)

  return (
    <div
      className={`search-result-item ${checked ? 'search-result-item--selected' : ''}`}
      data-testid="search-result-item"
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="search-result-item__checkbox"
        data-testid="result-checkbox"
      />
      <div className="search-result-item__content">
        <div className="search-result-item__header">
          <PixelBadge type={match.classification} />
          <span className="search-result-item__chapter" data-testid="result-chapter">
            {match.chapter}
          </span>
          <span className="search-result-item__source">{match.source}</span>
        </div>
        <div className="search-result-item__confidence">
          <div
            className="search-result-item__confidence-bar"
            style={{ width: `${confidencePct}%` }}
            data-testid="confidence-bar"
          />
          <span className="search-result-item__confidence-label">{confidencePct}%</span>
        </div>
        {match.reason && (
          <p className="search-result-item__reason" data-testid="result-reason">
            {match.reason}
          </p>
        )}
      </div>
    </div>
  )
}

export default SearchResults
