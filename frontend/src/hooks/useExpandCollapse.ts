import { useState, useCallback } from 'react'
import type { Node, Edge } from '@xyflow/react'

interface UseExpandCollapseReturn {
  applyVisibility: (nodes: Node[], edges: Edge[]) => { nodes: Node[]; edges: Edge[] }
  toggleChapter: (nodeId: string) => void
  expandedChapters: Set<string>
  isChapterExpanded: (nodeId: string) => boolean
}

export function useExpandCollapse(): UseExpandCollapseReturn {
  const [expandedChapters, setExpandedChapters] = useState<Set<string>>(new Set())

  const toggleChapter = useCallback((nodeId: string) => {
    setExpandedChapters((prev) => {
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
      const nodeToChapter = new Map<string, string>()
      nodes.forEach((node) => {
        if (node.type !== 'chapter') {
          const chapterId = (node.data as { concept?: { sourceChapterId?: string } })?.concept
            ?.sourceChapterId
          if (chapterId) nodeToChapter.set(node.id, chapterId)
        }
      })

      const visibleNodes = nodes.map((node) => {
        if (node.type === 'chapter') {
          return { ...node, hidden: false }
        }
        const parentChapterId = nodeToChapter.get(node.id)
        const isVisible = parentChapterId ? expandedChapters.has(parentChapterId) : true
        return { ...node, hidden: !isVisible }
      })

      const visibleNodeIds = new Set(visibleNodes.filter((n) => !n.hidden).map((n) => n.id))
      const visibleEdges = edges.map((edge) => ({
        ...edge,
        hidden: !visibleNodeIds.has(edge.source) || !visibleNodeIds.has(edge.target),
      }))

      return { nodes: visibleNodes, edges: visibleEdges }
    },
    [expandedChapters]
  )

  return {
    applyVisibility,
    toggleChapter,
    expandedChapters,
    isChapterExpanded: (nodeId: string) => expandedChapters.has(nodeId),
  }
}
