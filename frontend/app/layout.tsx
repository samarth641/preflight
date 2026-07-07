import type { Metadata } from "next"
import "./globals.css"
import { Sidebar } from "@/components/layout/Sidebar"

// Root layout — wraps every page with the sidebar.
// To add a new page/route, add it to navItems in components/layout/Sidebar.tsx.

export const metadata: Metadata = {
  title: "PreFlight — AI Training Intelligence",
  description: "AI-powered prediction and optimization for ML training",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
