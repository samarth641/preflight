import { Loader2 } from "lucide-react"

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`w-5 h-5 animate-spin text-[var(--primary)] ${className}`} />
}

export function FullSpinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <Spinner className="w-8 h-8" />
      <p className="text-sm text-[var(--text-muted)]">{label}</p>
    </div>
  )
}
