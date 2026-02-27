const API_BASE = 'http://localhost:8000/api'

export interface ChapterContent {
  textbook_id: string
  chapter_num: string
  title: string
  text: string
  image_urls: string[]
  page_start: number
  page_end: number
}

/** Fetch the text + image references for a specific chapter. */
export async function getChapterContent(
  textbookId: string,
  chapterNum: string
): Promise<ChapterContent> {
  const response = await fetch(
    `${API_BASE}/textbooks/${textbookId}/chapters/${chapterNum}/content`
  )
  if (!response.ok) {
    throw new Error(`Failed to load chapter: ${response.statusText}`)
  }
  return response.json()
}
