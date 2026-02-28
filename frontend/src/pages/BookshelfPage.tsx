import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCourses, type Course } from '../api/courses'
import { PixelButton } from '../components/pixel'
import { PixelPanel } from '../components/pixel'
import '../styles/bookshelf.css'

export function BookshelfPage() {
  const navigate = useNavigate()

  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewState, setViewState] = useState<'home' | 'preview'>('home')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dialog states (Tasks 8/9/10 will wire these — just declare them)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)

  const loadCourses = async () => {
    try {
      setIsLoading(true)
      const data = await getCourses()
      setCourses(data)
    } catch (err) {
      setError('Failed to load courses')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCourses()
  }, [])

  const filteredCourses = courses.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  )
  const selectedCourse = courses.find(c => c.id === selectedCourseId) ?? null
  const isMathLibrary = selectedCourse?.name === 'Math Library'

  // Suppress unused variable warnings — these will be wired in Tasks 8/9/10
  void isCreateDialogOpen
  void isUploadDialogOpen
  void isDeleteDialogOpen

  return (
    <div className="bookshelf-page">
      {/* Settings button — top-right */}
      <button
        className="settings-btn"
        onClick={() => navigate('/settings')}
        title="Settings"
        aria-label="Settings"
      >
        ⚙
      </button>

      {viewState === 'home' ? (
        <div className="bookshelf-grid">
          {/* LEFT COLUMN — Course Sidebar */}
          <div className="course-sidebar">
            <div className="sidebar-header">
              <h2 className="sidebar-title">Courses</h2>
            </div>

            <input
              className="course-search-input"
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search courses"
            />

            <div className="course-list">
              {isLoading && <p className="sidebar-message">Loading...</p>}
              {error && <p className="sidebar-message sidebar-error">{error}</p>}
              {!isLoading && !error && filteredCourses.length === 0 && (
                <p className="sidebar-message">No courses found.</p>
              )}
              {filteredCourses.map(course => (
                <div
                  key={course.id}
                  className={`course-item${selectedCourseId === course.id ? ' selected' : ''}`}
                  onClick={() => setSelectedCourseId(course.id)}
                  onDoubleClick={() => {
                    setSelectedCourseId(course.id)
                    setViewState('preview')
                  }}
                  tabIndex={0}
                  role="button"
                  aria-pressed={selectedCourseId === course.id}
                  title={course.name}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      setSelectedCourseId(course.id)
                      setViewState('preview')
                    } else if (e.key === ' ') {
                      e.preventDefault()
                      setSelectedCourseId(course.id)
                    } else if (e.key === 'Escape') {
                      setSelectedCourseId(null)
                    }
                  }}
                >
                  <span className="course-item-name">{course.name}</span>
                  <span className="course-item-count">{course.textbook_count} books</span>
                </div>
              ))}
            </div>

            {/* Action buttons */}
            <div className="sidebar-actions">
              <PixelButton
                variant="primary"
                onClick={() => setIsCreateDialogOpen(true)}
              >
                + New Course
              </PixelButton>

              {selectedCourseId && !isMathLibrary && (
                <>
                  <PixelButton
                    variant="secondary"
                    onClick={() => setIsUploadDialogOpen(true)}
                  >
                    Upload
                  </PixelButton>
                  <PixelButton
                    variant="secondary"
                    onClick={() => setViewState('preview')}
                  >
                    Select Course
                  </PixelButton>
                  <PixelButton
                    variant="danger"
                    onClick={() => setIsDeleteDialogOpen(true)}
                  >
                    Delete
                  </PixelButton>
                </>
              )}

              {selectedCourseId && isMathLibrary && (
                <PixelButton
                  variant="secondary"
                  onClick={() => setViewState('preview')}
                >
                  Select Course
                </PixelButton>
              )}
            </div>
          </div>

          {/* MIDDLE COLUMN — Scenery + Study Desk */}
          <div className="scenery-area">
            <div className="scenery-placeholder">
              {/* CSS pixel art scenery will be added in Task 12 */}
              {selectedCourse ? (
                <p className="scenery-prompt">
                  Double-click a course to preview it
                </p>
              ) : (
                <p className="scenery-prompt">
                  Select a course to begin
                </p>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN — Reserve Space */}
          <PixelPanel className="reserve-space">
            <p className="coming-soon-text">Coming Soon</p>
          </PixelPanel>
        </div>
      ) : (
        /* COURSE PREVIEW VIEW — placeholder, Task 11 will implement */
        <div className="course-preview-placeholder">
          <PixelButton variant="secondary" onClick={() => setViewState('home')}>
            ← Back
          </PixelButton>
          <p>Course Preview — {selectedCourse?.name}</p>
        </div>
      )}
    </div>
  )
}

export default BookshelfPage
