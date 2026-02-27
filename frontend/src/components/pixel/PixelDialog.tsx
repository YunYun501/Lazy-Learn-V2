import { useEffect } from 'react'
import '../../styles/pixel-components.css'

interface PixelDialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function PixelDialog({ isOpen, onClose, title, children }: PixelDialogProps) {
  // ESC key to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="pixel-dialog-overlay" onClick={onClose}>
      <div className="pixel-dialog" onClick={(e) => e.stopPropagation()}>
        {title && <div className="pixel-dialog__title">{title}</div>}
        <button className="pixel-dialog__close" onClick={onClose}>✕</button>
        {children}
      </div>
    </div>
  )
}
