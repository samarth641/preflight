import { AlertTriangle, Info, XCircle, CheckCircle2 } from "lucide-react"
import { ReactNode } from "react"

type Severity = "info" | "warning" | "error" | "success"

interface AlertProps {
  severity: Severity
  title?: string
  children: ReactNode
  className?: string
}

const config: Record<Severity, { icon: typeof Info; color: string; bg: string; border: string }> = {
  info: { icon: Info, color: "var(--info)", bg: "rgba(6, 182, 212, 0.08)", border: "rgba(6, 182, 212, 0.3)" },
  warning: { icon: AlertTriangle, color: "var(--warning)", bg: "rgba(245, 158, 11, 0.08)", border: "rgba(245, 158, 11, 0.3)" },
  error: { icon: XCircle, color: "var(--danger)", bg: "rgba(239, 68, 68, 0.08)", border: "rgba(239, 68, 68, 0.3)" },
  success: { icon: CheckCircle2, color: "var(--success)", bg: "rgba(34, 197, 94, 0.08)", border: "rgba(34, 197, 94, 0.3)" },
}

export function Alert({ severity, title, children, className = "" }: AlertProps) {
  const { icon: Icon, color, bg, border } = config[severity]
  return (
    <div className={`flex gap-3 p-4 rounded-lg border ${className}`} style={{ background: bg, borderColor: border }}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" style={{ color }} />
      <div className="flex-1">
        {title && <div className="text-sm font-medium mb-1" style={{ color }}>{title}</div>}
        <div className="text-sm text-[var(--text-secondary)]">{children}</div>
      </div>
    </div>
  )
}
