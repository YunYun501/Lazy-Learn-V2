import '../../styles/pixel-components.css'

interface PixelInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  multiline?: boolean
  rows?: number
  className?: string
}

export function PixelInput({
  value,
  onChange,
  placeholder = '',
  multiline = false,
  rows = 4,
  className = '',
}: PixelInputProps) {
  if (multiline) {
    return (
      <textarea
        className={`pixel-input ${className}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
      />
    )
  }
  return (
    <input
      type="text"
      className={`pixel-input ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  )
}
