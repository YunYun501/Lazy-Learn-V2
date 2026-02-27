import '../../styles/pixel-components.css'

interface PixelBadgeProps {
  type: 'EXPLAINS' | 'USES'
  className?: string
}

export function PixelBadge({ type, className = '' }: PixelBadgeProps) {
  const variantClass = type === 'EXPLAINS' ? 'pixel-badge--explains' : 'pixel-badge--uses'
  return (
    <span className={`pixel-badge ${variantClass} ${className}`} data-testid={`badge-${type}`}>
      {type}
    </span>
  )
}
