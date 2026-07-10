// Formatting utility functions

export function formatUSD(n: number): string {
  if (n >= 1000) return `$${(n / 1000).toFixed(1)}K`
  return `$${n.toFixed(2)}`
}

export function formatHours(n: number): string {
  if (n < 1) return `${Math.round(n * 60)} min`
  const h = Math.floor(n)
  const m = Math.round((n - h) * 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

export function formatPercent(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`
}

export function formatGB(n: number): string {
  return `${n.toFixed(1)} GB`
}

export function formatNumber(n: number): string {
  return n.toLocaleString()
}

export function formatRelativeTime(timestamp: string): string {
  const now = new Date()
  const past = new Date(timestamp)
  const diffMs = now.getTime() - past.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffMin < 1) return "just now"
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return past.toLocaleDateString()
}

export function gradeColor(grade: string): string {
  switch (grade) {
    case "A": return "var(--success)"
    case "B": return "var(--success)"
    case "C": return "var(--warning)"
    case "D": return "var(--warning)"
    case "F": return "var(--danger)"
    default: return "var(--text-muted)"
  }
}

export function fitRatingColor(rating: string): string {
  switch (rating) {
    case "excellent": return "var(--success)"
    case "good": return "var(--primary)"
    case "tight": return "var(--warning)"
    case "overkill": return "var(--text-muted)"
    case "insufficient": return "var(--danger)"
    default: return "var(--text-muted)"
  }
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "critical": return "var(--danger)"
    case "high": return "var(--warning)"
    case "medium": return "var(--warning)"
    case "low": return "var(--info)"
    default: return "var(--text-muted)"
  }
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed": return "var(--success)"
    case "running": return "var(--primary)"
    case "failed": return "var(--danger)"
    case "stopped": return "var(--text-muted)"
    default: return "var(--text-muted)"
  }
}

export function confidencePercent(n: number): string {
  return `${Math.round(n * 100)}%`
}
