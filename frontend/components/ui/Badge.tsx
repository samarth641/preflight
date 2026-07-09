import { ReactNode } from "react"

type Variant = "default" | "success" | "warning" | "danger" | "info" | "muted"

interface BadgeProps {
  children: ReactNode
  variant?: Variant
  className?: string
}

const variantStyles: Record<Variant, string> = {
  default: "bg-[var(--primary)]/10 text-[var(--primary)] border-[var(--primary)]/30",
  success: "bg-[var(--success)]/10 text-[var(--success)] border-[var(--success)]/30",
  warning: "bg-[var(--warning)]/10 text-[var(--warning)] border-[var(--warning)]/30",
  danger: "bg-[var(--danger)]/10 text-[var(--danger)] border-[var(--danger)]/30",
  info: "bg-[var(--info)]/10 text-[var(--info)] border-[var(--info)]/30",
  muted: "bg-[var(--text-muted)]/10 text-[var(--text-muted)] border-[var(--text-muted)]/30",
}

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  )
}
