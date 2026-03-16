import ChapterNode from './ChapterNode'
import ConceptNode from './ConceptNode'
import EquationNode from './EquationNode'

export const nodeTypes = {
  chapter: ChapterNode,
  concept: ConceptNode,
  equation: EquationNode,
} as const

export type NodeTypeName = keyof typeof nodeTypes
