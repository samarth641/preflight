"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, FlaskConical, FolderSearch, Cpu, Activity, History, Settings, Zap } from "lucide-react"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyze", label: "Analyze", icon: FlaskConical },
  { href: "/dataset", label: "Dataset", icon: FolderSearch },
  { href: "/gpu", label: "GPU Advisor", icon: Cpu },
  { href: "/training", label: "Training", icon: Activity },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-[var(--border)]">
        <div className="w-8 h-8 rounded-lg bg-[var(--primary)] flex items-center justify-center">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="text-sm font-semibold text-[var(--text)]">PreFlight</div>
          <div className="text-xs text-[var(--text-muted)]">AI Training Copilot</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-[var(--primary)] text-white font-medium"
                  : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
              }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Backend Status */}
      <div className="p-3 border-t border-[var(--border)]">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg)] text-xs">
          <div className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
          <span className="text-[var(--text-muted)]">Backend: Mock Mode</span>
        </div>
      </div>
    </aside>
  )
}
