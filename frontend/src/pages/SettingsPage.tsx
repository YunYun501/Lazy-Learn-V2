import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PixelButton, PixelPanel } from '../components/pixel'
import { getSettings, updateSetting, testConnection, type SettingsMap } from '../api/settings'
import { getTextbooks } from '../api/textbooks'

// ─── Types ────────────────────────────────────────────────────────────────────

type FeedbackState = { type: 'success' | 'error'; msg: string } | null
type TestState = { provider: string; success: boolean; msg: string } | null

// ─── SettingsPage ─────────────────────────────────────────────────────────────

export function SettingsPage() {
  const navigate = useNavigate()

  // Settings state
  const [currentSettings, setCurrentSettings] = useState<SettingsMap>({})
  const [deepseekKey, setDeepseekKey] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [downloadFolder, setDownloadFolder] = useState('')
  const [courses, setCourses] = useState<string[]>([])

  // UI state
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<FeedbackState>(null)
  const [testState, setTestState] = useState<TestState>(null)
  const [testingProvider, setTestingProvider] = useState<string | null>(null)

  // Load settings and courses on mount
  useEffect(() => {
    loadSettings()
    loadCourses()
  }, [])

  // ESC key → navigate back
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') navigate('/')
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [navigate])

  async function loadSettings() {
    try {
      const data = await getSettings()
      setCurrentSettings(data)
      setDownloadFolder(data.download_folder ?? '')
    } catch {
      // Backend may not be running; ignore silently
    }
  }

  async function loadCourses() {
    try {
      const books = await getTextbooks()
      const unique = [...new Set(books.map(b => b.course).filter(Boolean) as string[])]
      setCourses(unique.sort())
    } catch {
      // Ignore
    }
  }

  async function handleSave() {
    setSaving(true)
    setFeedback(null)
    try {
      const updates: Promise<unknown>[] = []

      if (deepseekKey.trim()) {
        updates.push(updateSetting('deepseek_api_key', deepseekKey.trim()))
      }
      if (openaiKey.trim()) {
        updates.push(updateSetting('openai_api_key', openaiKey.trim()))
      }
      // Always save download folder (even empty, to clear it)
      updates.push(updateSetting('download_folder', downloadFolder))

      await Promise.all(updates)

      // Reload to get fresh masked values
      const fresh = await getSettings()
      setCurrentSettings(fresh)
      setDeepseekKey('')
      setOpenaiKey('')
      setFeedback({ type: 'success', msg: 'Settings saved!' })
    } catch {
      setFeedback({ type: 'error', msg: 'Failed to save settings.' })
    } finally {
      setSaving(false)
    }
  }

  async function handleTestConnection(provider: 'deepseek' | 'openai') {
    setTestingProvider(provider)
    setTestState(null)
    try {
      const result = await testConnection(provider)
      setTestState({ provider, success: result.success, msg: result.message })
    } catch {
      setTestState({ provider, success: false, msg: 'Connection test failed.' })
    } finally {
      setTestingProvider(null)
    }
  }

  const hasDeepseekKey = !!currentSettings.deepseek_api_key
  const hasOpenaiKey = !!currentSettings.openai_api_key

  return (
    <div className="settings-page" data-testid="settings-page" style={styles.page}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.gearIcon}>⚙</span>
          <h1 style={styles.title}>SETTINGS</h1>
        </div>
        <button
          style={styles.closeBtn}
          onClick={() => navigate('/')}
          aria-label="Close settings"
        >
          ✕ ESC
        </button>
      </header>

      <div style={styles.content}>

        {/* ── API Keys Section ─────────────────────────────────────── */}
        <PixelPanel style={styles.section}>
          <h2 style={styles.sectionTitle}>API KEYS</h2>
          <p style={styles.sectionHint}>
            Keys are stored locally and masked in this view.
          </p>

          {/* DeepSeek Key */}
          <div style={styles.fieldGroup}>
            <label style={styles.label}>DEEPSEEK API KEY</label>
            {hasDeepseekKey && (
              <div style={styles.existingKey}>
                CURRENT: <span style={styles.maskedKey}>{currentSettings.deepseek_api_key}</span>
              </div>
            )}
            <div style={styles.inputRow}>
              <input
                type="password"
                className="pixel-input"
                style={styles.keyInput}
                value={deepseekKey}
                onChange={e => setDeepseekKey(e.target.value)}
                placeholder={hasDeepseekKey ? 'Enter new key to replace…' : 'sk-…'}
                data-testid="deepseek-key-input"
                autoComplete="new-password"
              />
              <div data-testid="test-deepseek-btn">
                <PixelButton
                  variant="secondary"
                  onClick={() => handleTestConnection('deepseek')}
                  disabled={testingProvider === 'deepseek'}
                >
                  {testingProvider === 'deepseek' ? 'TESTING…' : 'TEST'}
                </PixelButton>
              </div>
            </div>
            {testState?.provider === 'deepseek' && (
              <div style={testState.success ? styles.testSuccess : styles.testError}>
                {testState.success ? '✓' : '✗'} {testState.msg}
              </div>
            )}
          </div>

          {/* OpenAI Key */}
          <div style={styles.fieldGroup}>
            <label style={styles.label}>OPENAI API KEY <span style={styles.optional}>(optional)</span></label>
            {hasOpenaiKey && (
              <div style={styles.existingKey}>
                CURRENT: <span style={styles.maskedKey}>{currentSettings.openai_api_key}</span>
              </div>
            )}
            <div style={styles.inputRow}>
              <input
                type="password"
                className="pixel-input"
                style={styles.keyInput}
                value={openaiKey}
                onChange={e => setOpenaiKey(e.target.value)}
                placeholder={hasOpenaiKey ? 'Enter new key to replace…' : 'sk-…'}
                data-testid="openai-key-input"
                autoComplete="new-password"
              />
              <div data-testid="test-openai-btn">
                <PixelButton
                  variant="secondary"
                  onClick={() => handleTestConnection('openai')}
                  disabled={testingProvider === 'openai'}
                >
                  {testingProvider === 'openai' ? 'TESTING…' : 'TEST'}
                </PixelButton>
              </div>
            </div>
            {testState?.provider === 'openai' && (
              <div style={testState.success ? styles.testSuccess : styles.testError}>
                {testState.success ? '✓' : '✗'} {testState.msg}
              </div>
            )}
          </div>
        </PixelPanel>

        {/* ── Download Folder Section ──────────────────────────────── */}
        <PixelPanel style={styles.section}>
          <h2 style={styles.sectionTitle}>DOWNLOAD FOLDER</h2>
          <p style={styles.sectionHint}>Default directory for saving study data.</p>
          <input
            type="text"
            className="pixel-input"
            style={styles.fullInput}
            value={downloadFolder}
            onChange={e => setDownloadFolder(e.target.value)}
            placeholder="/path/to/data/folder"
            data-testid="download-folder-input"
          />
        </PixelPanel>

        {/* ── Courses Section ──────────────────────────────────────── */}
        <PixelPanel style={styles.section}>
          <h2 style={styles.sectionTitle}>COURSES</h2>
          <p style={styles.sectionHint}>Courses from imported textbooks (read-only).</p>
          {courses.length === 0 ? (
            <p style={styles.emptyCourses}>No courses yet — import a textbook to get started.</p>
          ) : (
            <ul style={styles.courseList}>
              {courses.map(course => (
                <li key={course} style={styles.courseItem}>
                  <span style={styles.courseBullet}>▶</span>
                  {course}
                </li>
              ))}
            </ul>
          )}
        </PixelPanel>

        {/* ── Save Button & Feedback ───────────────────────────────── */}
        <div style={styles.saveRow}>
          {feedback && (
            <div style={feedback.type === 'success' ? styles.feedbackSuccess : styles.feedbackError}>
              {feedback.type === 'success' ? '✓' : '✗'} {feedback.msg}
            </div>
          )}
          <div data-testid="save-btn">
            <PixelButton
              variant="primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'SAVING…' : '💾 SAVE SETTINGS'}
            </PixelButton>
          </div>
        </div>

      </div>
    </div>
  )
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: 'var(--color-bg-primary)',
    color: 'var(--color-text-primary)',
    fontFamily: 'var(--font-content)',
    padding: '0',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '24px 32px',
    background: 'var(--color-bg-secondary)',
    borderBottom: '3px solid var(--color-border)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  gearIcon: {
    fontSize: '24px',
    lineHeight: 1,
  },
  title: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '14px',
    color: 'var(--color-text-primary)',
    margin: 0,
    letterSpacing: '2px',
  },
  closeBtn: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '10px',
    background: 'transparent',
    color: 'var(--color-text-secondary)',
    border: '2px solid var(--color-border)',
    padding: '6px 12px',
    cursor: 'pointer',
    letterSpacing: '1px',
  },
  content: {
    maxWidth: '720px',
    margin: '0 auto',
    padding: '32px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  section: {
    padding: '24px',
  },
  sectionTitle: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '12px',
    color: 'var(--color-accent-primary)',
    margin: '0 0 8px 0',
    letterSpacing: '2px',
  },
  sectionHint: {
    fontFamily: 'var(--font-content)',
    fontSize: '13px',
    color: 'var(--color-text-secondary)',
    margin: '0 0 20px 0',
  },
  fieldGroup: {
    marginBottom: '24px',
  },
  label: {
    display: 'block',
    fontFamily: 'var(--font-pixel)',
    fontSize: '9px',
    color: 'var(--color-text-secondary)',
    marginBottom: '8px',
    letterSpacing: '1px',
  },
  optional: {
    color: 'var(--color-text-muted)',
    fontSize: '8px',
  },
  existingKey: {
    fontFamily: 'var(--font-mono)',
    fontSize: '11px',
    color: 'var(--color-text-secondary)',
    marginBottom: '8px',
    padding: '6px 10px',
    background: 'var(--color-bg-secondary)',
    border: '1px solid var(--color-border)',
  },
  maskedKey: {
    color: 'var(--color-accent-secondary)',
    letterSpacing: '1px',
  },
  inputRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-start',
  },
  keyInput: {
    flex: 1,
    minWidth: 0,
  },
  fullInput: {
    width: '100%',
  },
  testSuccess: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '9px',
    color: 'var(--color-accent-green)',
    marginTop: '8px',
    letterSpacing: '1px',
  },
  testError: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '9px',
    color: 'var(--color-accent-primary)',
    marginTop: '8px',
    letterSpacing: '1px',
  },
  emptyCourses: {
    fontFamily: 'var(--font-content)',
    fontSize: '13px',
    color: 'var(--color-text-muted)',
    margin: 0,
  },
  courseList: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  courseItem: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '10px',
    color: 'var(--color-text-primary)',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    background: 'var(--color-bg-secondary)',
    border: '2px solid var(--color-border)',
    letterSpacing: '1px',
  },
  courseBullet: {
    color: 'var(--color-accent-secondary)',
    fontSize: '8px',
  },
  saveRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '20px',
    paddingTop: '8px',
  },
  feedbackSuccess: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '9px',
    color: 'var(--color-accent-green)',
    letterSpacing: '1px',
  },
  feedbackError: {
    fontFamily: 'var(--font-pixel)',
    fontSize: '9px',
    color: 'var(--color-accent-primary)',
    letterSpacing: '1px',
  },
}

export default SettingsPage
