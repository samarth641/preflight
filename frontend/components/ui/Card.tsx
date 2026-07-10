import { ReactNode } from "react"

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
  action?: ReactNode
}

export function Card({ children, className = "", title, action }: CardProps) {
  return (
    <div className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 ${className}`}>
      {title && (
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-sm font-semibold text-[var(--text)]">{title}</h3>
          {action}
        </div>
      )}
      {children}
    </div>
  )
}
