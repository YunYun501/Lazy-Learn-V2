const BASE_URL = 'http://127.0.0.1:8000'

export interface UniversityMaterial {
  id: string
  course_id: string
  title: string
  file_type: string
  filepath: string
  created_at: string
}

export async function getUniversityMaterials(courseId: string): Promise<UniversityMaterial[]> {
  const res = await fetch(`${BASE_URL}/api/university-materials?course_id=${encodeURIComponent(courseId)}`)
  if (!res.ok) throw new Error(`Failed to fetch materials: ${res.status}`)
  return res.json()
}

export async function uploadUniversityMaterial(file: File, courseId: string): Promise<UniversityMaterial> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('course_id', courseId)
  const res = await fetch(`${BASE_URL}/api/university-materials/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function deleteUniversityMaterial(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/university-materials/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Failed to delete: ${res.status}`)
  }
}
