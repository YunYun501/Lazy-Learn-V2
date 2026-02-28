import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCourses, createCourse, deleteCourse, type Course } from '../api/courses'
import { importTextbook, getImportStatus } from '../api/textbooks'
import { uploadUniversityMaterial } from '../api/universityMaterials'
import { PixelButton, PixelDialog } from '../components/pixel'
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
  const [newCourseName, setNewCourseName] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [uploadStep, setUploadStep] = useState<'choice' | 'textbook' | 'material'>('choice')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

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

  const handleCreateCourse = async () => {
    const name = newCourseName.trim()
    if (!name) {
      setCreateError('Course name cannot be empty')
      return
    }
    try {
      setIsCreating(true)
      setCreateError(null)
      await createCourse(name)
      setIsCreateDialogOpen(false)
      setNewCourseName('')
      await loadCourses()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create course'
      setCreateError(msg)
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteCourse = async () => {
    if (!selectedCourseId) return
    try {
      setIsDeleting(true)
      setDeleteError(null)
      await deleteCourse(selectedCourseId)
      setIsDeleteDialogOpen(false)
      setSelectedCourseId(null)
      await loadCourses()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to delete course'
      setDeleteError(msg)
    } finally {
      setIsDeleting(false)
    }
  }

  // File input refs for upload dialog
  const textbookInputRef = React.useRef<HTMLInputElement>(null)
  const materialInputRef = React.useRef<HTMLInputElement>(null)

  const handleTextbookFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedCourseId) return
    try {
      setIsUploading(true)
      setUploadError(null)
      await importTextbook(file, selectedCourseId)
      setIsUploadDialogOpen(false)
      setUploadStep('choice')
      // Refresh courses to show updated textbook count
      await loadCourses()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setUploadError(msg)
    } finally {
      setIsUploading(false)
      // Reset file input
      if (textbookInputRef.current) textbookInputRef.current.value = ''
    }
  }

  const handleMaterialFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedCourseId) return
    try {
      setIsUploading(true)
      setUploadError(null)
      await uploadUniversityMaterial(file, selectedCourseId)
      setIsUploadDialogOpen(false)
      setUploadStep('choice')
      await loadCourses()
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setUploadError(msg)
    } finally {
      setIsUploading(false)
      if (materialInputRef.current) materialInputRef.current.value = ''
    }
  }

  const filteredCourses = courses.filter(c =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  )
  const selectedCourse = courses.find(c => c.id === selectedCourseId) ?? null
  const isMathLibrary = selectedCourse?.name === 'Math Library'


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

      {/* Create Course Dialog */}
      <PixelDialog
        isOpen={isCreateDialogOpen}
        onClose={() => {
          setIsCreateDialogOpen(false)
          setNewCourseName('')
          setCreateError(null)
        }}
        title="New Course"
      >
        <div className="dialog-form">
          <input
            className="dialog-input"
            type="text"
            placeholder="Course name..."
            value={newCourseName}
            onChange={(e) => setNewCourseName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateCourse()
              if (e.key === 'Escape') {
                setIsCreateDialogOpen(false)
                setNewCourseName('')
                setCreateError(null)
              }
            }}
            autoFocus
            data-testid="create-course-input"
          />
          {createError && <p className="dialog-error">{createError}</p>}
          <div className="dialog-actions">
            <PixelButton
              variant="primary"
              onClick={handleCreateCourse}
              disabled={isCreating}
              data-testid="create-course-submit"
            >
              {isCreating ? '...' : 'Create'}
            </PixelButton>
            <PixelButton
              variant="secondary"
              onClick={() => {
                setIsCreateDialogOpen(false)
                setNewCourseName('')
                setCreateError(null)
              }}
            >
              Cancel
            </PixelButton>
          </div>
        </div>
      </PixelDialog>

      {/* Upload Dialog */}
      <PixelDialog
        isOpen={isUploadDialogOpen}
        onClose={() => {
          setIsUploadDialogOpen(false)
          setUploadStep('choice')
          setUploadError(null)
        }}
        title={uploadStep === 'choice' ? 'Upload Content' : uploadStep === 'textbook' ? 'Upload Textbook' : 'Upload Material'}
      >
        <div className="dialog-form">
          {uploadStep === 'choice' && (
            <>
              <p className="dialog-prompt">What would you like to upload?</p>
              <div className="upload-choice-buttons">
                <PixelButton variant="primary" onClick={() => setUploadStep('textbook')}>
                  📚 Textbook
                </PixelButton>
                <PixelButton variant="secondary" onClick={() => setUploadStep('material')}>
                  📄 University Material
                </PixelButton>
              </div>
            </>
          )}
          {uploadStep === 'textbook' && (
            <>
              <p className="dialog-prompt">Select a PDF textbook file:</p>
              <input
                ref={textbookInputRef}
                type="file"
                accept=".pdf"
                onChange={handleTextbookFileSelected}
                style={{ display: 'none' }}
                data-testid="textbook-file-input"
              />
              <PixelButton
                variant="primary"
                onClick={() => textbookInputRef.current?.click()}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Choose PDF'}
              </PixelButton>
              {uploadError && <p className="dialog-error">{uploadError}</p>}
              <PixelButton variant="secondary" onClick={() => setUploadStep('choice')}>
                ← Back
              </PixelButton>
            </>
          )}
          {uploadStep === 'material' && (
            <>
              <p className="dialog-prompt">Select a university material file:</p>
              <input
                ref={materialInputRef}
                type="file"
                accept=".pdf,.pptx,.docx,.txt,.md,.xlsx"
                onChange={handleMaterialFileSelected}
                style={{ display: 'none' }}
                data-testid="material-file-input"
              />
              <PixelButton
                variant="primary"
                onClick={() => materialInputRef.current?.click()}
                disabled={isUploading}
              >
                {isUploading ? 'Uploading...' : 'Choose File'}
              </PixelButton>
              {uploadError && <p className="dialog-error">{uploadError}</p>}
              <PixelButton variant="secondary" onClick={() => setUploadStep('choice')}>
                ← Back
              </PixelButton>
            </>
          )}
        </div>
      </PixelDialog>

      {/* Delete Confirmation Dialog */}
      <PixelDialog
        isOpen={isDeleteDialogOpen}
        onClose={() => {
          setIsDeleteDialogOpen(false)
          setDeleteError(null)
        }}
        title="Delete Course"
      >
        <div className="dialog-form">
          <p className="dialog-prompt">
            Delete "{selectedCourse?.name}"?
          </p>
          <p className="dialog-warning">
            This will permanently remove all textbooks, university materials, and associated data.
          </p>
          {deleteError && <p className="dialog-error">{deleteError}</p>}
          <div className="dialog-actions">
            <PixelButton
              variant="danger"
              onClick={handleDeleteCourse}
              disabled={isDeleting}
              data-testid="delete-course-confirm"
            >
              {isDeleting ? '...' : 'Delete'}
            </PixelButton>
            <PixelButton
              variant="secondary"
              onClick={() => {
                setIsDeleteDialogOpen(false)
                setDeleteError(null)
              }}
            >
              Cancel
            </PixelButton>
          </div>
        </div>
      </PixelDialog>
    </div>
  )
}

export default BookshelfPage
