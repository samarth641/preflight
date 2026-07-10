"use client"

import { useState } from "react"
import { CheckCircle2, AlertCircle, LogOut } from "lucide-react"
import { useAuth } from "@/components/providers/AuthProvider"

interface TopBarProps {
  title: string
  subtitle?: string
}

function UserMenu() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)

  if (!user) return null

  const initials = (user.displayName || user.email || "?")
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()

  const handleSignOut = async () => {
    setSigningOut(true)
    try {
      await signOut()
    } finally {
      setSigningOut(false)
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-[var(--surface-hover)] transition-colors"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {user.photoURL ? (
          <img
            src={user.photoURL}
            alt=""
            className="w-8 h-8 rounded-full object-cover"
            referrerPolicy="no-referrer"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs font-medium">
            {initials}
          </div>
        )}
        <span className="text-xs text-[var(--text-secondary)] max-w-[120px] truncate hidden sm:inline">
          {user.displayName || user.email}
        </span>
      </button>

      {open && (
        <>
          <button
            type="button"
            className="fixed inset-0 z-10 cursor-default"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 z-20 w-56 rounded-lg border border-[var(--border)] bg-[var(--surface)] shadow-lg py-1">
            <div className="px-3 py-2 border-b border-[var(--border)]">
              <p className="text-sm font-medium text-[var(--text)] truncate">
                {user.displayName || "Signed in"}
              </p>
              <p className="text-xs text-[var(--text-muted)] truncate">{user.email}</p>
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              disabled={signingOut}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]"
            >
              <LogOut className="w-4 h-4" />
              {signingOut ? "Signing out..." : "Sign out"}
            </button>
          </div>
        </>
      )}
    </div>
  )
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
          <span>v0.2.0</span>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <AlertCircle className="w-4 h-4 text-[var(--warning)]" />
          <span>23 rules loaded</span>
        </div>
        <UserMenu />
      </div>
    </header>
  )
}
