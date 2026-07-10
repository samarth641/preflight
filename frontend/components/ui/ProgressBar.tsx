interface ProgressBarProps {
  value: number
  max?: number
  label?: string
  color?: string
  showValue?: boolean
}

export function ProgressBar({ value, max = 100, label, color = "var(--primary)", showValue = true }: ProgressBarProps) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div>
      {label && (
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-[var(--text-secondary)]">{label}</span>
          {showValue && <span className="text-[var(--text-muted)] font-mono">{value.toFixed(0)}{max === 100 ? "%" : ""}</span>}
        </div>
      )}
      <div className="h-2 rounded-full bg-[var(--bg)] overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}
