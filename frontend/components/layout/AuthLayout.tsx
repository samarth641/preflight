"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { Sidebar } from "@/components/layout/Sidebar"
import { FullSpinner } from "@/components/ui/Spinner"
import { useAuth } from "@/components/providers/AuthProvider"

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, authOptional } = useAuth()
  const pathname = usePathname()
  const router = useRouter()
  const isLoginPage = pathname === "/login"

  useEffect(() => {
    if (loading) return
    if (authOptional) {
      if (isLoginPage) router.replace("/")
      return
    }
    if (!user && !isLoginPage) router.replace("/login")
    if (user && isLoginPage) router.replace("/")
  }, [user, loading, authOptional, isLoginPage, router])

  if (loading) {
    return <FullSpinner label="Loading PreFlight..." />
  }

  if (isLoginPage) {
    return <>{children}</>
  }

  if (!user && !authOptional) {
    return <FullSpinner label="Redirecting to sign in..." />
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 min-w-0">{children}</main>
    </div>
  )
}
