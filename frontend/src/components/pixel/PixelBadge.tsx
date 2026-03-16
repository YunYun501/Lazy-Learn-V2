import type { ReactNode } from 'react'
import '../../styles/pixel-components.css'

interface PixelBadgeProps {
  type: 'EXPLAINS' | 'USES'
  className?: string
  children?: ReactNode
}

export function PixelBadge({ type, className = '', children }: PixelBadgeProps) {
  const variantClass = type === 'EXPLAINS' ? 'pixel-badge--explains' : 'pixel-badge--uses'
  return (
    <span className={`pixel-badge ${variantClass} ${className}`} data-testid={`badge-${type}`}>
      {children ?? type}
    </span>
  )
}
