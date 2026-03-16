import ChapterNode from './ChapterNode'
import ConceptNode from './ConceptNode'

export const nodeTypes = {
  chapter: ChapterNode,
  concept: ConceptNode,
} as const

export type NodeTypeName = keyof typeof nodeTypes
