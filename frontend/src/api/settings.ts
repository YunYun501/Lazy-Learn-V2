const BASE_URL = 'http://127.0.0.1:8000'

export interface SettingsMap {
  deepseek_api_key?: string
  openai_api_key?: string
  download_folder?: string
  [key: string]: string | undefined
}

export interface ConnectionTestResult {
  success: boolean
  message: string
}

export async function getSettings(): Promise<SettingsMap> {
  const res = await fetch(`${BASE_URL}/api/settings`)
  if (!res.ok) throw new Error(`Failed to fetch settings: ${res.status}`)
  return res.json()
}

export async function updateSetting(key: string, value: string): Promise<{ success: boolean; key: string }> {
  const res = await fetch(`${BASE_URL}/api/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value }),
  })
  if (!res.ok) throw new Error(`Failed to update setting: ${res.status}`)
  return res.json()
}

export async function testConnection(provider: 'deepseek' | 'openai'): Promise<ConnectionTestResult> {
  const res = await fetch(`${BASE_URL}/api/settings/test-connection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  })
  if (!res.ok) throw new Error(`Failed to test connection: ${res.status}`)
  return res.json()
}
