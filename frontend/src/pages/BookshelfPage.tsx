import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTextbooks, importTextbook, getImportStatus, type Textbook } from '../api/textbooks'
import { PixelButton, PixelPanel } from '../components/pixel'
import '../styles/bookshelf.css'

const BOOK_COLORS = [
  '#e94560', '#f5a623', '#4caf50', '#2196f3', '#9c27b0',
  '#00bcd4', '#ff5722', '#8bc34a', '#3f51b5', '#ff9800',
]

function BookSpine({ textbook, index, onClick }: { textbook: Textbook; index: number; onClick: () => void }) {
  const color = BOOK_COLORS[index % BOOK_COLORS.length]
  const shortTitle = textbook.title.length > 20
    ? textbook.title.slice(0, 18) + '…'
    : textbook.title

  return (
    <button
      className="book-spine"
      style={{ '--book-color': color } as React.CSSProperties}
      onClick={onClick}
      title={textbook.title}
      data-testid="book-spine"
    >
      <span className="book-title">{shortTitle}</span>
      {textbook.course && <span className="book-course">{textbook.course}</span>}
    </button>
  )
}

export function BookshelfPage() {
  const navigate = useNavigate()
  const [textbooks, setTextbooks] = useState<Textbook[]>([])
  const [loading, setLoading] = useState(true)
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
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
        if (status.status === 'complete' || status.status === 'error' || attempts > 60) {
          clearInterval(poll)
          setImporting(false)
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
    }
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const courseBooks = textbooks.filter(t => t.library_type !== 'math')
  const mathBooks = textbooks.filter(t => t.library_type === 'math')

  return (
    <div className="bookshelf-page" data-testid="bookshelf-page">
      <header className="bookshelf-header">
        <h1 className="bookshelf-title">LAZY LEARN</h1>
        <p className="bookshelf-subtitle">AI-Powered STEM Study Assistant</p>
      </header>

      {error && (
        <div className="bookshelf-error" role="alert">
          {error}
        </div>
      )}

      {/* Math Library shelf */}
      <section className="shelf-section">
        <h2 className="shelf-label">MATH LIBRARY</h2>
        <PixelPanel className="shelf">
          {mathBooks.length === 0 ? (
            <p className="shelf-empty">No math references yet</p>
          ) : (
            mathBooks.map((book, i) => (
              <BookSpine
                key={book.id}
                textbook={book}
                index={i}
                onClick={() => navigate(`/desk/${book.id}`)}
              />
            ))
          )}
        </PixelPanel>
      </section>

      {/* Course books shelf */}
      <section className="shelf-section">
        <h2 className="shelf-label">COURSE BOOKS</h2>
        <PixelPanel className="shelf">
          {loading ? (
            <p className="shelf-empty">Loading…</p>
          ) : courseBooks.length === 0 ? (
            <p className="shelf-empty">No textbooks yet — import one below!</p>
          ) : (
            courseBooks.map((book, i) => (
              <BookSpine
                key={book.id}
                textbook={book}
                index={i}
                onClick={() => navigate(`/desk/${book.id}`)}
              />
            ))
          )}
        </PixelPanel>
      </section>

      {/* Import button */}
      <div className="bookshelf-actions">
        <PixelButton
          onClick={() => fileInputRef.current?.click()}
          disabled={importing}
          variant="primary"
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
    </div>
  )
}

export default BookshelfPage
