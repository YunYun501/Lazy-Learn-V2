import '../../styles/pixel-components.css'

interface PixelPanelProps {
  children: React.ReactNode
  variant?: 'default' | 'bright' | 'accent'
  className?: string
  style?: React.CSSProperties
}

export function PixelPanel({
  children,
  variant = 'default',
  className = '',
  style,
}: PixelPanelProps) {
  const variantClass = variant !== 'default' ? `pixel-panel--${variant}` : ''
  return (
    <div className={`pixel-panel ${variantClass} ${className}`} style={style}>
      {children}
    </div>
  )
}
