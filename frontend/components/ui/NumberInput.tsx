"use client"

import { useEffect, useState } from "react"

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
  const [text, setText] = useState(() => String(value))

  useEffect(() => {
    setText((prev) => {
      const parsed = parseFloat(prev)
      // Keep local draft while the user is clearing/editing (empty, trailing dot, etc.)
      if (prev === "" || prev === "-" || prev.endsWith(".")) return prev
      if (!Number.isNaN(parsed) && parsed === value) return prev
      return String(value)
    })
  }, [value])

  function commit(raw: string) {
    if (raw === "" || raw === "-" || raw === "." || raw === "-.") {
      const fallback = min ?? 0
      setText(String(fallback))
      onChange(fallback)
      return
    }
    const n = parseFloat(raw)
    if (Number.isNaN(n)) {
      const fallback = min ?? 0
      setText(String(fallback))
      onChange(fallback)
      return
    }
    let next = n
    if (min !== undefined && next < min) next = min
    if (max !== undefined && next > max) next = max
    setText(String(next))
    onChange(next)
  }

  return (
    <div className={className}>
      {label && <label className="block text-xs text-[var(--text-secondary)] mb-1.5">{label}</label>}
      <input
        type="number"
        value={text}
        step={step}
        min={min}
        max={max}
        onChange={(e) => {
          const raw = e.target.value
          setText(raw)
          if (raw === "" || raw === "-" || raw === "." || raw === "-.") return
          const n = parseFloat(raw)
          if (!Number.isNaN(n)) onChange(n)
        }}
        onBlur={() => commit(text)}
        className="w-full px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)] font-mono"
      />
    </div>
  )
}
