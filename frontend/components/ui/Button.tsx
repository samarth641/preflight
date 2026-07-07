import { ReactNode } from "react"
import { Loader2 } from "lucide-react"

type Variant = "primary" | "secondary" | "danger"

interface ButtonProps {
  children: ReactNode
  onClick?: () => void
  variant?: Variant
  loading?: boolean
  disabled?: boolean
  className?: string
  type?: "button" | "submit"
}

const variantStyles: Record<Variant, string> = {
  primary: "bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]",
  secondary: "bg-[var(--surface-hover)] text-[var(--text)] hover:bg-[var(--border)] border border-[var(--border)]",
  danger: "bg-[var(--danger)] text-white hover:bg-red-600",
}

export function Button({ children, onClick, variant = "primary", loading, disabled, className = "", type = "button" }: ButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variantStyles[variant]} ${className}`}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  )
}
