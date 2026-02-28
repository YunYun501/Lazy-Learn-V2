import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCourses, createCourse, deleteCourse, type Course } from '../api/courses'
import { importTextbook, getImportStatus, getTextbooks, type Textbook } from '../api/textbooks'
import { uploadUniversityMaterial, getUniversityMaterials, type UniversityMaterial } from '../api/universityMaterials'
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
  const [uploadProgress, setUploadProgress] = useState<Record<string, {jobId: string, progress: number, step: string, error: boolean}>>({})

  // Preview view state
  const [previewTextbooks, setPreviewTextbooks] = useState<Textbook[]>([])
  const [previewMaterials, setPreviewMaterials] = useState<UniversityMaterial[]>([])
  const [selectedTextbookId, setSelectedTextbookId] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

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

  // Escape key → back to home view
  useEffect(() => {
    if (viewState !== 'preview') return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setViewState('home')
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [viewState])

  // Fetch preview data when entering preview mode
  useEffect(() => {
    if (viewState !== 'preview' || !selectedCourseId) return
    setPreviewTextbooks([])
    setPreviewMaterials([])
    setSelectedTextbookId(null)
    setPreviewLoading(true)
    Promise.all([
      getTextbooks().then(all => all.filter(t => t.course_id === selectedCourseId)),
      getUniversityMaterials(selectedCourseId),
    ])
      .then(([textbooks, materials]) => {
        setPreviewTextbooks(textbooks)
        setPreviewMaterials(materials)
      })
      .catch(() => {})
      .finally(() => setPreviewLoading(false))
  }, [viewState, selectedCourseId])

  // Poll active upload jobs every 2 seconds
  useEffect(() => {
    const activeJobs = Object.entries(uploadProgress).filter(([, v]) => v.progress < 100 && !v.error)
    if (activeJobs.length === 0) return
    const interval = setInterval(async () => {
      for (const [courseId, info] of activeJobs) {
        try {
          const status = await getImportStatus(info.jobId)
          if (status.status === 'complete') {
            setUploadProgress(prev => { const n = {...prev}; delete n[courseId]; return n })
            loadCourses()
          } else if (status.status === 'error') {
            setUploadProgress(prev => ({...prev, [courseId]: {...prev[courseId], error: true}}))
          } else {
            setUploadProgress(prev => ({...prev, [courseId]: {
              ...prev[courseId],
              progress: status.progress ?? prev[courseId].progress,
              step: status.step ?? prev[courseId].step,
            }}))
          }
        } catch {}
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [uploadProgress])

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
      const job = await importTextbook(file, selectedCourseId)
      setUploadProgress(prev => ({
        ...prev,
        [selectedCourseId]: { jobId: job.job_id, progress: 0, step: 'Starting...', error: false }
      }))
      setIsUploadDialogOpen(false)
      setUploadStep('choice')
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
                  className={`course-item${selectedCourseId === course.id ? ' selected' : ''}${uploadProgress[course.id]?.error ? ' upload-error' : ''}`}
                  style={uploadProgress[course.id] && !uploadProgress[course.id].error ? { background: `linear-gradient(to right, var(--color-accent-secondary) ${uploadProgress[course.id].progress}%, var(--color-bg-panel) ${uploadProgress[course.id].progress}%)` } : undefined}
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
                  {uploadProgress[course.id] && <span className="course-item-progress">{uploadProgress[course.id].step}</span>}
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
              <div className="scene-container">
                <div className="scene-window">
                  <div className="scene-star scene-star-1" />
                  <div className="scene-star scene-star-2" />
                  <div className="scene-star scene-star-3" />
                  <div className="scene-star scene-star-4" />
                  <div className="scene-star scene-star-5" />
                </div>
                <div className="scene-desk">
                  <div className="scene-lamp">
                    <div className="scene-lamp-head" />
                    <div className="scene-lamp-arm" />
                    <div className="scene-lamp-base" />
                  </div>
                  <div className="scene-lamp-glow" />
                  <div className="scene-book" />
                  <div className="scene-book scene-book-2" />
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN — Reserve Space */}
          <PixelPanel className="reserve-space">
            <p className="coming-soon-text">Coming Soon</p>
          </PixelPanel>
        </div>
      ) : (
        /* COURSE PREVIEW VIEW */
        <div className="course-preview-view">
          {/* Sidebar — mirrors home sidebar, shows course list */}
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
                  className={`course-item${selectedCourseId === course.id ? ' selected' : ''}${uploadProgress[course.id]?.error ? ' upload-error' : ''}`}
                  style={uploadProgress[course.id] && !uploadProgress[course.id].error ? { background: `linear-gradient(to right, var(--color-accent-secondary) ${uploadProgress[course.id].progress}%, var(--color-bg-panel) ${uploadProgress[course.id].progress}%)` } : undefined}
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
                      setViewState('home')
                    }
                  }}
                >
                  <span className="course-item-name">{course.name}</span>
                  <span className="course-item-count">{course.textbook_count} books</span>
                  {uploadProgress[course.id] && <span className="course-item-progress">{uploadProgress[course.id].step}</span>}
                </div>
              ))}
            </div>

            <div className="sidebar-actions">
              <PixelButton variant="secondary" onClick={() => setViewState('home')}>
                ← Back
              </PixelButton>
            </div>
          </div>

          {/* Preview Content */}
          <div className="preview-content">
            <div className="preview-header">
              <h2 className="preview-course-title">{selectedCourse?.name}</h2>
            </div>

            <div className="preview-panels">
              {/* Panel 1: Textbooks */}
              <PixelPanel className="textbooks-panel">
                <h3 className="panel-title">Textbooks</h3>
                {previewLoading && <p className="panel-message">Loading...</p>}
                {!previewLoading && previewTextbooks.length === 0 && (
                  <p className="panel-message">No textbooks uploaded yet.</p>
                )}
                <div className="preview-list">
                  {previewTextbooks.map(tb => (
                    <div
                      key={tb.id}
                      className={`preview-textbook-item${selectedTextbookId === tb.id ? ' selected' : ''}`}
                      onClick={() => setSelectedTextbookId(tb.id)}
                      tabIndex={0}
                      role="button"
                      aria-pressed={selectedTextbookId === tb.id}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          setSelectedTextbookId(tb.id)
                        }
                      }}
                    >
                      <span className="textbook-item-title">{tb.title}</span>
                    </div>
                  ))}
                </div>
                <div className="panel-footer">
                  <PixelButton
                    variant="primary"
                    disabled={!selectedTextbookId}
                    onClick={() => {
                      if (selectedTextbookId) navigate('/desk/' + selectedTextbookId)
                    }}
                  >
                    Begin Study
                  </PixelButton>
                </div>
              </PixelPanel>

              {/* Panel 2: University Materials */}
              <PixelPanel className="materials-panel">
                <h3 className="panel-title">University Content</h3>
                {previewLoading && <p className="panel-message">Loading...</p>}
                {!previewLoading && previewMaterials.length === 0 && (
                  <p className="panel-message">No materials uploaded yet.</p>
                )}
                <div className="preview-list">
                  {previewMaterials.map(m => (
                    <div key={m.id} className="preview-material-item">
                      <span className="material-item-title">{m.title}</span>
                      <div className="material-item-meta">
                        <span className="material-type-badge">{m.file_type.toUpperCase()}</span>
                        <span className="material-item-date">
                          {new Date(m.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </PixelPanel>

              {/* Panel 3: TBD */}
              <PixelPanel className="tbd-panel">
                <h3 className="panel-title">More</h3>
                <p className="panel-message">More features coming soon</p>
              </PixelPanel>
            </div>
          </div>
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
