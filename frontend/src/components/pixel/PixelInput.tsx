import '../../styles/pixel-components.css'

interface PixelInputProps {
  value: string
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  placeholder?: string
  multiline?: boolean
  rows?: number
  className?: string
}

export function PixelInput({
  value,
  onChange,
  onKeyDown,
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
        onChange={onChange as React.ChangeEventHandler<HTMLTextAreaElement>}
        onKeyDown={onKeyDown as React.KeyboardEventHandler<HTMLTextAreaElement>}
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
      onChange={onChange as React.ChangeEventHandler<HTMLInputElement>}
      onKeyDown={onKeyDown as React.KeyboardEventHandler<HTMLInputElement>}
      placeholder={placeholder}
    />
  )
}
