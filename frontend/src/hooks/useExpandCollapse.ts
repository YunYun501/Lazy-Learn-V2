import { useState, useCallback, useRef } from 'react'
import type { Node, Edge } from '@xyflow/react'
import type { ConceptNodeData } from '../types/knowledgeGraph'

interface UseExpandCollapseReturn {
  applyVisibility: (nodes: Node[], edges: Edge[]) => { nodes: Node[]; edges: Edge[] }
  toggleChapter: (nodeId: string) => void
  toggleSection: (nodeId: string) => void
  expandedChapters: Set<string>
  expandedSections: Set<string>
  isChapterExpanded: (nodeId: string) => boolean
  isSectionExpanded: (nodeId: string) => boolean
}

export function useExpandCollapse(): UseExpandCollapseReturn {
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set())
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const sectionToChapterRef = useRef<Map<string, string>>(new Map())

  const toggleChapter = useCallback((nodeId: string) => {
    setExpandedChapters((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
        setExpandedSections((prevSections) => {
          const nextSections = new Set(prevSections)
          sectionToChapterRef.current.forEach((chapterId, sectionId) => {
            if (chapterId === nodeId) nextSections.delete(sectionId)
          })
          return nextSections
        })
      } else {
        next.add(nodeId)
      }
      return next
    })
  }, [])

  const toggleSection = useCallback((nodeId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }, [])

  const applyVisibility = useCallback(
    (nodes: Node[], edges: Edge[]) => {
      const nodeToParentChapter = new Map<string, string>()
      const nodeToParentSection = new Map<string, string>()
      const sectionToChapter = new Map<string, string>()
      nodes.forEach((node) => {
        const concept = (node.data as ConceptNodeData | undefined)?.concept
        if (!concept) return
        const { level, sourceChapterId, sourceSectionId } = concept
        if (level !== 'chapter' && sourceChapterId) {
          nodeToParentChapter.set(node.id, sourceChapterId)
        }
        if (level === 'section') {
          if (sourceChapterId) sectionToChapter.set(node.id, sourceChapterId)
        } else if (sourceSectionId) {
          nodeToParentSection.set(node.id, sourceSectionId)
        }
      })
      sectionToChapterRef.current = sectionToChapter

      const visibleNodes = nodes.map((node) => {
        const concept = (node.data as ConceptNodeData | undefined)?.concept
        if (node.type === 'chapter' || concept?.level === 'chapter') {
          return { ...node, hidden: false }
        }
        const parentChapterId = nodeToParentChapter.get(node.id)
        const parentSectionId = nodeToParentSection.get(node.id)
        const isChapterVisible = parentChapterId ? expandedChapters.has(parentChapterId) : true
        if (concept?.level === 'section') {
          return { ...node, hidden: !isChapterVisible }
        }
        const isSectionVisible = parentSectionId ? expandedSections.has(parentSectionId) : true
        const isVisible = isChapterVisible && isSectionVisible
        return { ...node, hidden: !isVisible }
      })

      const visibleNodeIds = new Set(visibleNodes.filter((n) => !n.hidden).map((n) => n.id))
      const visibleEdges = edges.map((edge) => ({
        ...edge,
        hidden: !visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target),
      }))

      return { nodes: visibleNodes, edges: visibleEdges }
    },
    [expandedChapters, expandedSections]
  )

  return {
    applyVisibility,
    toggleChapter,
    toggleSection,
    expandedChapters,
    expandedSections,
    isChapterExpanded: (nodeId: string) => expandedChapters.has(nodeId),
    isSectionExpanded: (nodeId: string) => expandedSections.has(nodeId),
  }
}
