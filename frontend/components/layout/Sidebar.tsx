"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, FlaskConical, FolderSearch, Cpu, Activity, History, Settings, ChevronDown, ChevronRight, Clock, Rocket } from "lucide-react"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyze", label: "Analyze", icon: FlaskConical, children: [
    { href: "/analyze/ml-duration", label: "ML Duration", icon: Clock },
    { href: "/analyze/pre-training", label: "Pre-Training", icon: Rocket },
  ]},
  { href: "/dataset", label: "Dataset", icon: FolderSearch },
  { href: "/gpu", label: "GPU Advisor", icon: Cpu },
  { href: "/training", label: "Training", icon: Activity },
  { href: "/history", label: "History", icon: History },
  { href: "/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [analyzeOpen, setAnalyzeOpen] = useState(true)

  useEffect(() => {
    if (!pathname.startsWith("/analyze")) {
      setAnalyzeOpen(false)
    }
  }, [pathname])

  return (
    <aside className="w-60 shrink-0 border-r border-[var(--border)] bg-[var(--surface)] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="h-16 flex items-center gap-3 px-5 border-b border-[var(--border)]">
        <div className="w-9 h-9 rounded-lg bg-[var(--primary)] flex items-center justify-center shrink-0">
          {/* Paper plane — angular, upward trajectory. Represents "pre-flight" prep before launching training. */}
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 11.5L21 4L13.5 22L10.5 14.5L3 11.5Z" fill="white" fillOpacity="0.15" />
            <path d="M3 11.5L21 4L10.5 14.5" />
            <path d="M10.5 14.5L13.5 22" />
            <path d="M3 11.5L10.5 14.5" strokeOpacity="0.6" />
          </svg>
        </div>
        <div>
          <div className="text-base font-bold text-[var(--text)]">PreFlight</div>
          <div className="text-xs text-[var(--text-muted)]">AI Training Copilot</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon

          // Analyze item with dropdown
          if (item.children) {
            const parentActive = pathname.startsWith(item.href)
            return (
              <div key={item.href}>
                <button
                  onClick={() => setAnalyzeOpen(!analyzeOpen)}
                  className={`relative w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                    parentActive
                      ? "bg-[var(--primary-soft)] text-[var(--text)] font-medium"
                      : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
                  }`}
                >
                  {parentActive && <span className="nav-active-bar" />}
                  <Icon className={`w-4 h-4 shrink-0 ${parentActive ? "text-[var(--primary)]" : ""}`} />
                  <span className="flex-1 text-left">{item.label}</span>
                  {analyzeOpen ? <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)]" /> : <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />}
                </button>
                {analyzeOpen && (
                  <div className="ml-4 mt-0.5 space-y-0.5 border-l border-[var(--border)] pl-3">
                    {item.children.map((child) => {
                      const ChildIcon = child.icon
                      const childActive = pathname === child.href
                      return (
                        <Link
                          key={child.href}
                          href={child.href}
                          className={`relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all ${
                            childActive
                              ? "bg-[var(--primary-soft)] text-[var(--text)] font-medium"
                              : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
                          }`}
                        >
                          <ChildIcon className={`w-3.5 h-3.5 shrink-0 ${childActive ? "text-[var(--primary)]" : ""}`} />
                          <span>{child.label}</span>
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          }

          // Regular nav item
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                active
                  ? "bg-[var(--primary-soft)] text-[var(--text)] font-medium"
                  : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
              }`}
            >
              {active && <span className="nav-active-bar" />}
              <Icon className={`w-4 h-4 shrink-0 ${active ? "text-[var(--primary)]" : ""}`} />
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
