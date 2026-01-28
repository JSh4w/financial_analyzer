import { colors, borderRadius, typography } from '../theme'

interface SearchBarProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  status?: string
  placeholder?: string
}

export default function SearchBar({
  value,
  onChange,
  onSubmit,
  status,
  placeholder = 'Search for stocks...',
}: SearchBarProps) {
  return (
    <div
      style={{
        padding: '16px 24px',
        backgroundColor: colors.bg.secondary,
        borderBottom: `1px solid ${colors.border.default}`,
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
      }}
    >
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            onSubmit()
          }
        }}
        placeholder={placeholder}
        style={{
          flex: 1,
          maxWidth: '600px',
          padding: '12px 16px',
          fontSize: typography.fontSize.sm,
          backgroundColor: colors.bg.primary,
          color: colors.text.primary,
          border: `1px solid ${colors.border.default}`,
          borderRadius: borderRadius.lg,
          outline: 'none',
          transition: 'border-color 0.2s ease',
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = colors.accent.primary
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = colors.border.default
        }}
      />
      {status && (
        <span
          style={{
            fontSize: typography.fontSize.sm,
            color: colors.text.tertiary,
          }}
        >
          {status}
        </span>
      )}
    </div>
  )
}
