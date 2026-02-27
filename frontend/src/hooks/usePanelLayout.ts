import { useState, useCallback } from 'react'

export type PanelContentType = 'ai' | 'textbook' | 'empty'

export interface PanelState {
  type: PanelContentType
  chapterId?: string
}

export interface PanelLayoutState {
  panelA: PanelState
  panelB: PanelState
  merged: boolean
  swapPanels: () => void
  toggleMerge: () => void
  setPanelA: (state: PanelState) => void
  setPanelB: (state: PanelState) => void
}

export function usePanelLayout(): PanelLayoutState {
  const [panelA, setPanelA] = useState<PanelState>({ type: 'ai' })
  const [panelB, setPanelB] = useState<PanelState>({ type: 'textbook' })
  const [merged, setMerged] = useState(false)

  const swapPanels = useCallback(() => {
    setPanelA(prev => {
      setPanelB(prev)
      return panelB
    })
  }, [panelB])

  const toggleMerge = useCallback(() => {
    setMerged(prev => !prev)
  }, [])

  return {
    panelA,
    panelB,
    merged,
    swapPanels,
    toggleMerge,
    setPanelA,
    setPanelB,
  }
}
