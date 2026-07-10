"use client"

import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--bg)] relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 20% 20%, rgba(59,130,246,0.25), transparent 50%), radial-gradient(ellipse 50% 40% at 80% 80%, rgba(6,182,212,0.15), transparent 50%)",
        }}
      />

      <div className="relative w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-2xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-11 h-11 rounded-xl bg-[var(--primary)] flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.8">
              <path d="M3 11.5L21 4L13.5 22L10.5 14.5L3 11.5Z" fill="white" fillOpacity="0.15" />
              <path d="M3 11.5L21 4L10.5 14.5" />
              <path d="M10.5 14.5L13.5 22" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--text)]">PreFlight</h1>
            <p className="text-sm text-[var(--text-muted)]">AI Training Copilot</p>
          </div>
        </div>

        <h2 className="text-lg font-semibold text-[var(--text)] mb-2">Sign in to continue</h2>
        <p className="text-sm text-[var(--text-secondary)] mb-6">
          Use your Google account to access GPU recommendations, training monitor, and dataset analysis.
        </p>

        <GoogleSignInButton />

        <p className="mt-6 text-xs text-center text-[var(--text-muted)]">
          Secured by Firebase Authentication
        </p>
      </div>
    </div>
  )
}
