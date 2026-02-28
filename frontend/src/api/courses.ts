const BASE_URL = 'http://127.0.0.1:8000'

export interface Course {
  id: string
  name: string
  created_at: string
  textbook_count: number
  material_count: number
}

export async function getCourses(): Promise<Course[]> {
  const res = await fetch(`${BASE_URL}/api/courses`)
  if (!res.ok) throw new Error(`Failed to fetch courses: ${res.status}`)
  return res.json()
}

export async function getCourse(id: string): Promise<Course> {
  const res = await fetch(`${BASE_URL}/api/courses/${id}`)
  if (!res.ok) throw new Error(`Failed to fetch course: ${res.status}`)
  return res.json()
}

export async function createCourse(name: string): Promise<Course> {
  const res = await fetch(`${BASE_URL}/api/courses`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function updateCourse(id: string, name: string): Promise<Course> {
  const res = await fetch(`${BASE_URL}/api/courses/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Server error ${res.status}`)
  }
  return res.json()
}

export async function deleteCourse(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/courses/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Failed to delete: ${res.status}`)
  }
}
