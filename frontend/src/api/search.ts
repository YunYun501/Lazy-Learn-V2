const API_BASE = 'http://localhost:8000/api'

export interface CategorizedMatch {
  source: string
  chapter: string
  subchapter: string
  classification: 'EXPLAINS' | 'USES'
  confidence: number
  reason: string
  textbook_id?: string
  chapter_num?: string
}

export interface SearchResults {
  query: string
  matches: CategorizedMatch[]
}

/** Run the full hybrid search pipeline (Steps 0-2) for a query. */
export async function searchQuery(query: string): Promise<SearchResults> {
  const response = await fetch(`${API_BASE}/search/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`)
  }
  return response.json()
}

export interface ChapterRef {
  textbook_id: string
  chapter_num: string
  classification: string
  textbook_title?: string
}

/** Stream an AI explanation for selected chapters. Returns a ReadableStream of SSE chunks. */
export function generateExplanation(
  chapters: ChapterRef[],
  query: string
): Promise<ReadableStream<Uint8Array>> {
  return fetch(`${API_BASE}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chapters, query }),
  }).then((res) => {
    if (!res.ok) throw new Error(`Explain failed: ${res.statusText}`)
    if (!res.body) throw new Error('No response body')
    return res.body
  })
}
