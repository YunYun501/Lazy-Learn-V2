import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PixelButton, PixelPanel } from './pixel'
import { ChapterVerification } from './ChapterVerification'
import { verifyChapters } from '../api/pipeline'
import { PipelineProgress } from './PipelineProgress'
import type { Course } from '../api/courses'
import type { Textbook } from '../api/textbooks'
import type { UniversityMaterial } from '../api/universityMaterials'
import type { PipelineStatus, ChapterWithStatus } from '../types/pipeline'

export interface CoursePreviewViewProps {
  course: Course | null
  textbooks: Textbook[]
  materials: UniversityMaterial[]
  onBack: () => void
  onBeginStudy: (textbookId: string) => void
  onUpload: () => void
  onDelete: () => void
  isLoading?: boolean
  pipelineStatus?: PipelineStatus
  pipelineChapters?: ChapterWithStatus[]
  pipelineTextbookId?: string
}

export function CoursePreviewView({
  course,
  textbooks,
  materials,
  onBack,
  onBeginStudy,
  onUpload,
  onDelete,
  isLoading = false,
  pipelineStatus,
  pipelineChapters,
  pipelineTextbookId,
}: CoursePreviewViewProps) {
  const navigate = useNavigate()
  const [selectedTextbookId, setSelectedTextbookId] = useState<string | null>(null)

  const handleBeginStudy = () => {
    if (selectedTextbookId) {
      onBeginStudy(selectedTextbookId)
      navigate('/desk/' + selectedTextbookId)
    }
  }

  const handleVerifyChapters = async (selectedIds: string[]) => {
    if (!pipelineTextbookId) return
    try {
      await verifyChapters(pipelineTextbookId, selectedIds)
    } catch (error) {
      console.error('Failed to verify chapters:', error)
    }
    onBack()
  }

  const showVerification =
    pipelineStatus === 'toc_extracted' ||
    pipelineStatus === 'awaiting_verification'

  const showPipelineProgress =
    pipelineStatus === 'extracting' || pipelineStatus === 'partially_extracted'

  return (
    <div className="course-preview-view">
      {/* Sidebar — mirrors home sidebar, shows course list */}
      <div className="course-sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-title">Courses</h2>
        </div>

        <div className="sidebar-actions">
          <PixelButton variant="secondary" onClick={onBack}>
            ← Back
          </PixelButton>
        </div>
      </div>

      {/* Preview Content */}
      <div className="preview-content">
        <div className="preview-header">
          <h2 className="preview-course-title">{course?.name}</h2>
        </div>

        <div className="preview-panels">
          {showVerification ? (
            <ChapterVerification
              chapters={pipelineChapters ?? []}
              onConfirm={handleVerifyChapters}
              onBack={onBack}
            />
          ) : (
            <>
              {/* Panel 1: Textbooks */}
              <PixelPanel className="textbooks-panel">
                <h3 className="panel-title">Textbooks</h3>
                {showPipelineProgress && pipelineTextbookId && pipelineChapters ? (
                  <PipelineProgress
                    textbookId={pipelineTextbookId}
                    initialStatus={pipelineStatus!}
                    chapters={pipelineChapters}
                  />
                ) : (
                  <>
                    {isLoading && <p className="panel-message">Loading...</p>}
                    {!isLoading && textbooks.length === 0 && (
                      <p className="panel-message">No textbooks uploaded yet.</p>
                    )}
                    <div className="preview-list">
                      {textbooks.map(tb => (
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
                        onClick={handleBeginStudy}
                      >
                        Begin Study
                      </PixelButton>
                    </div>
                  </>
                )}
              </PixelPanel>

              {/* Panel 2: University Materials */}
              <PixelPanel className="materials-panel">
                <h3 className="panel-title">University Content</h3>
                {isLoading && <p className="panel-message">Loading...</p>}
                {!isLoading && materials.length === 0 && (
                  <p className="panel-message">No materials uploaded yet.</p>
                )}
                <div className="preview-list">
                  {materials.map(m => (
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}
