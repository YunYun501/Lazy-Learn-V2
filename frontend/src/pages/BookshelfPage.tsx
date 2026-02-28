import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTextbooks, importTextbook, getImportStatus, deleteTextbook, type Textbook } from '../api/textbooks'
import { PixelButton } from '../components/pixel'
import '../styles/bookshelf.css'

const BOOK_COLORS = [
  '#e94560', '#f5a623', '#4caf50', '#2196f3', '#9c27b0',
  '#00bcd4', '#ff5722', '#8bc34a', '#3f51b5', '#ff9800',
]

function BookSpine({
  textbook,
  index,
  onClick,
  onDelete,
}: {
  textbook: Textbook
  index: number
  onClick: () => void
  onDelete: () => void
}) {
  const color = BOOK_COLORS[index % BOOK_COLORS.length]
  const shortTitle = textbook.title.length > 32
    ? textbook.title.slice(0, 30) + '…'
    : textbook.title

  return (
    <div
      className="book-spine"
      style={{ '--book-color': color } as React.CSSProperties}
      onClick={onClick}
      title={textbook.title}
      data-testid="book-spine"
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick() }}
    >
      <span className="book-title">{shortTitle}</span>
      {textbook.course && (
        <span className="book-course-tag">{textbook.course}</span>
      )}
      <button
        className="book-delete-btn"
        onClick={(e) => {
          e.stopPropagation()
          onDelete()
        }}
        title={`Remove "${textbook.title}"`}
        aria-label={`Delete ${textbook.title}`}
      >
        ✕
      </button>
    </div>
  )
}

export function BookshelfPage() {
  const navigate = useNavigate()
  const [textbooks, setTextbooks] = useState<Textbook[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [step, setStep] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadTextbooks()
  }, [])

  async function loadTextbooks() {
    try {
      setLoading(true)
      const books = await getTextbooks()
      setTextbooks(books)
    } catch (err) {
      setError('Failed to load textbooks. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(textbook: Textbook) {
    if (!window.confirm(`Remove "${textbook.title}"?`)) return
    try {
      await deleteTextbook(textbook.id)
      await loadTextbooks()
    } catch (err) {
      setError(`Failed to delete: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setImporting(true)
      setError(null)
      const job = await importTextbook(file)
      // Poll for completion
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        const status = await getImportStatus(job.job_id)

        // Show warning if flattened PDF detected
        if (status.warning) {
          setWarning(status.warning)
        }

        // Track progress
        if (status.progress !== undefined) {
          setProgress(status.progress)
        }
        if (status.step) {
          setStep(status.step)
        }

        if (status.status === 'complete' || status.status === 'error' || attempts > 60) {
          clearInterval(poll)
          setImporting(false)
          setWarning(null)  // Clear warning when done
          setProgress(0)
          setStep(null)
          if (status.status === 'error') {
            setError(`Import failed: ${status.error}`)
          } else {
            await loadTextbooks()
          }
        }
      }, 2000)
    } catch (err) {
      setError(`Import failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setImporting(false)
      setProgress(0)
      setStep(null)
    }
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const courseBooks = textbooks.filter(t => t.library_type !== 'math')
  const mathBooks = textbooks.filter(t => t.library_type === 'math')

  return (
    <div className="bookshelf-page" data-testid="bookshelf-page">

      {/* ── LEFT SIDEBAR ── */}
      <aside className="bookshelf-sidebar">
        <div className="sidebar-shelf-label">📚 BOOKSHELF</div>

        {/* Math Library */}
        <section className="shelf-section">
          <h2 className="shelf-label">MATH LIBRARY</h2>
          <div className="shelf-books">
            {mathBooks.length === 0 ? (
              <p className="shelf-empty">No math references yet</p>
            ) : (
              mathBooks.map((book, i) => (
                <BookSpine
                  key={book.id}
                  textbook={book}
                  index={i}
                  onClick={() => navigate(`/desk/${book.id}`)}
                  onDelete={() => handleDelete(book)}
                />
              ))
            )}
          </div>
        </section>

        {/* Course Books */}
        <section className="shelf-section">
          <h2 className="shelf-label">COURSE BOOKS</h2>
          <div className="shelf-books">
            {loading ? (
              <p className="shelf-empty">Loading…</p>
            ) : courseBooks.length === 0 ? (
              <p className="shelf-empty">No textbooks yet</p>
            ) : (
              courseBooks.map((book, i) => (
                <BookSpine
                  key={book.id}
                  textbook={book}
                  index={i}
                  onClick={() => navigate(`/desk/${book.id}`)}
                  onDelete={() => handleDelete(book)}
                />
              ))
            )}
          </div>
        </section>

        {/* Import at bottom of sidebar */}
        <div className="sidebar-actions">
          <PixelButton
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            variant="primary"
            className="sidebar-import-btn"
          >
            {importing ? 'IMPORTING…' : '+ IMPORT TEXTBOOK'}
          </PixelButton>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
            data-testid="file-input"
          />
        </div>
      </aside>

      {/* ── RIGHT MAIN CONTENT ── */}
      <main className="bookshelf-main">
        <header className="bookshelf-header" style={{ position: 'relative' }}>
          <h1 className="bookshelf-title">LAZY LEARN</h1>
          <p className="bookshelf-subtitle">AI-Powered STEM Study Assistant</p>
          <button
            onClick={() => navigate('/settings')}
            title="Open Settings"
            aria-label="Open settings"
            data-testid="settings-gear-btn"
            style={{
              position: 'absolute',
              top: '50%',
              right: '16px',
              transform: 'translateY(-50%)',
              background: 'transparent',
              border: '2px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
              fontSize: '20px',
              cursor: 'pointer',
              padding: '4px 8px',
              lineHeight: 1,
            }}
          >
            ⚙
          </button>
        </header>

        {error && (
          <div className="bookshelf-error" role="alert">
            {error}
          </div>
        )}

        {warning && (
          <div className="bookshelf-error" role="alert" style={{ backgroundColor: '#fff3cd', borderColor: '#ffc107', color: '#856404' }}>
            {warning}
          </div>
        )}

        {importing && (
          <div style={{
            margin: '16px 0',
            padding: '12px 16px',
            border: '2px solid var(--color-border, #333)',
            backgroundColor: 'var(--color-bg-secondary, #1a1a2e)',
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '8px',
              fontFamily: '"Press Start 2P", monospace',
              fontSize: '10px',
              color: 'var(--color-text-secondary, #aaa)',
            }}>
              <span>{step || 'Starting...'}</span>
              <span>{progress}%</span>
            </div>
            <div style={{
              width: '100%',
              height: '16px',
              backgroundColor: 'var(--color-bg, #0f0f23)',
              border: '2px solid var(--color-border, #333)',
              overflow: 'hidden',
            }}>
              <div style={{
                width: `${progress}%`,
                height: '100%',
                backgroundColor: '#4caf50',
                transition: 'width 0.5s ease-in-out',
                imageRendering: 'pixelated' as const,
                backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(0,0,0,0.15) 3px, rgba(0,0,0,0.15) 4px)',
              }} />
            </div>
          </div>
        )}

        {/* Welcome state */}
        {!loading && textbooks.length === 0 && (
          <div className="bookshelf-welcome">
            <div className="welcome-icon">📖</div>
            <p className="welcome-text">Your bookshelf is empty</p>
            <p className="welcome-hint">
              Import a PDF textbook using the button in the sidebar
              to start your AI-powered study session.
            </p>
            <div className="welcome-steps">
              <div className="welcome-step">
                <span className="step-num">01</span>
                <span className="step-desc">Import a textbook PDF</span>
              </div>
              <div className="welcome-step">
                <span className="step-num">02</span>
                <span className="step-desc">Click on a book to open your desk</span>
              </div>
              <div className="welcome-step">
                <span className="step-num">03</span>
                <span className="step-desc">Ask questions &amp; get instant explanations</span>
              </div>
            </div>
          </div>
        )}

        {/* Loaded state hint */}
        {!loading && textbooks.length > 0 && (
          <div className="bookshelf-hint">
            <p className="hint-text">
              ← Select a book from the shelf to open your study desk
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

export default BookshelfPage
