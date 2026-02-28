const BASE_URL = 'http://127.0.0.1:8000'

export interface Textbook {
  id: string
  title: string
  filepath: string
  course: string | null
  library_type: string
  processed_at: string | null
}

export interface ImportJob {
  textbook_id: string
  job_id: string
  message: string
}

export interface ImportStatus {
  textbook_id: string
  status: 'processing' | 'complete' | 'error' | 'not_found'
  chapters_found: number
  error?: string
  warning?: string
  progress?: number
  step?: string
}

export async function getTextbooks(course?: string): Promise<Textbook[]> {
  const url = course
    ? `${BASE_URL}/api/textbooks?course=${encodeURIComponent(course)}`
    : `${BASE_URL}/api/textbooks`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Failed to fetch textbooks: ${res.status}`)
  return res.json()
}

export async function importTextbook(file: File, course?: string): Promise<ImportJob> {
  const formData = new FormData()
  formData.append('file', file)
  if (course) formData.append('course', course)
  const res = await fetch(`${BASE_URL}/api/textbooks/import`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function getImportStatus(jobId: string): Promise<ImportStatus> {
  const res = await fetch(`${BASE_URL}/api/textbooks/${jobId}/status`)
  if (!res.ok) throw new Error(`Failed to get status: ${res.status}`)
  return res.json()
}

export async function deleteTextbook(textbookId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/textbooks/${textbookId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Failed to delete: ${res.status}`)
  }
}
