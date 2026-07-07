"use client"

import { CheckCircle2, AlertCircle } from "lucide-react"

interface TopBarProps {
  title: string
  subtitle?: string
}

export function TopBar({ title, subtitle }: TopBarProps) {
  return (
    <header className="h-16 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between px-6 sticky top-0 z-10">
      <div>
        <h1 className="text-lg font-semibold text-[var(--text)]">{title}</h1>
        {subtitle && <p className="text-xs text-[var(--text-muted)]">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <CheckCircle2 className="w-4 h-4 text-[var(--success)]" />
          <span>v0.1.0</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <AlertCircle className="w-4 h-4 text-[var(--warning)]" />
          <span>30 rules loaded</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs font-medium">
          ML
        </div>
      </div>
    </header>
  )
}
