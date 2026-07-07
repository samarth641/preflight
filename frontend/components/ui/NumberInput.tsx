interface NumberInputProps {
  value: number
  onChange: (value: number) => void
  label?: string
  step?: number
  min?: number
  max?: number
  className?: string
}

export function NumberInput({ value, onChange, label, step = 1, min, max, className = "" }: NumberInputProps) {
  return (
    <div className={className}>
      {label && <label className="block text-xs text-[var(--text-secondary)] mb-1.5">{label}</label>}
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-full px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)] font-mono"
      />
    </div>
  )
}
