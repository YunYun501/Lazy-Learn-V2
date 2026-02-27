import { useState, useCallback, useEffect } from 'react'

export interface PinnedImage {
  id: string
  src: string
  alt: string
}

export interface PinnedFormula {
  id: string
  label: string
  latex: string
}

export interface PinnedItemsState {
  pinnedImages: PinnedImage[]
  pinnedFormulas: PinnedFormula[]
  recentConcepts: string[]
  pinImage: (image: PinnedImage) => void
  unpinImage: (id: string) => void
  pinFormula: (formula: PinnedFormula) => void
  unpinFormula: (id: string) => void
  addRecentConcept: (concept: string) => void
}

const STORAGE_KEY = 'lazy-learn-pinned-items'

interface StoredState {
  pinnedImages: PinnedImage[]
  pinnedFormulas: PinnedFormula[]
  recentConcepts: string[]
}

function loadFromStorage(): StoredState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {
    // ignore
  }
  return { pinnedImages: [], pinnedFormulas: [], recentConcepts: [] }
}

export function usePinnedItems(): PinnedItemsState {
  const [state, setState] = useState<StoredState>(loadFromStorage)

  // Persist to localStorage whenever state changes
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      // ignore quota errors
    }
  }, [state])

  const pinImage = useCallback((image: PinnedImage) => {
    setState(prev => ({
      ...prev,
      pinnedImages: [...prev.pinnedImages.filter(i => i.id !== image.id), image],
    }))
  }, [])

  const unpinImage = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      pinnedImages: prev.pinnedImages.filter(i => i.id !== id),
    }))
  }, [])

  const pinFormula = useCallback((formula: PinnedFormula) => {
    setState(prev => ({
      ...prev,
      pinnedFormulas: [...prev.pinnedFormulas.filter(f => f.id !== formula.id), formula],
    }))
  }, [])

  const unpinFormula = useCallback((id: string) => {
    setState(prev => ({
      ...prev,
      pinnedFormulas: prev.pinnedFormulas.filter(f => f.id !== id),
    }))
  }, [])

  const addRecentConcept = useCallback((concept: string) => {
    setState(prev => {
      const filtered = prev.recentConcepts.filter(c => c !== concept)
      return {
        ...prev,
        recentConcepts: [concept, ...filtered].slice(0, 10), // Keep last 10
      }
    })
  }, [])

  return {
    pinnedImages: state.pinnedImages,
    pinnedFormulas: state.pinnedFormulas,
    recentConcepts: state.recentConcepts,
    pinImage,
    unpinImage,
    pinFormula,
    unpinFormula,
    addRecentConcept,
  }
}
