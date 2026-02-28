import type { ChapterWithStatus, PipelineStatus } from '../types/pipeline'

const BASE_URL = 'http://127.0.0.1:8000'

// ── Response types ───────────────────────────────────────────────────────

export interface TextbookStatusResponse {
  pipeline_status: PipelineStatus
  chapters: ChapterWithStatus[]
}

export interface VerifyResponse {
  status: string
  selected_count: number
}

export interface ExtractDeferredResponse {
  status: string
}

export interface ExtractionProgressResponse {
  pipeline_status: PipelineStatus
  chapters: ChapterWithStatus[]
}

// ── API functions ────────────────────────────────────────────────────────

export async function getTextbookStatus(
  textbookId: string
): Promise<TextbookStatusResponse> {
  const res = await fetch(`${BASE_URL}/api/textbooks/${textbookId}/status`)
  if (!res.ok) throw new Error(`Failed to fetch textbook status: ${res.status}`)
  return res.json()
}

export async function verifyChapters(
  textbookId: string,
  selectedChapterIds: string[]
): Promise<VerifyResponse> {
  const res = await fetch(
    `${BASE_URL}/api/textbooks/${textbookId}/verify-chapters`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_chapter_ids: selectedChapterIds }),
    }
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function extractDeferred(
  textbookId: string,
  chapterIds: string[]
): Promise<ExtractDeferredResponse> {
  const res = await fetch(
    `${BASE_URL}/api/textbooks/${textbookId}/extract-deferred`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chapter_ids: chapterIds }),
    }
  )
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function getExtractionProgress(
  textbookId: string
): Promise<ExtractionProgressResponse> {
  const res = await fetch(
    `${BASE_URL}/api/textbooks/${textbookId}/extraction-progress`
  )
  if (!res.ok)
    throw new Error(`Failed to fetch extraction progress: ${res.status}`)
  return res.json()
}
