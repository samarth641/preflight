import type { Metadata } from "next"
import "./globals.css"
import { AuthLayout } from "@/components/layout/AuthLayout"
import { AuthProvider } from "@/components/providers/AuthProvider"
import { PageResultsProvider } from "@/components/providers/PageResultsContext"

export const metadata: Metadata = {
  title: "PreFlight — AI Training Intelligence",
  description: "AI-powered prediction and optimization for ML training",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <PageResultsProvider>
            <AuthLayout>{children}</AuthLayout>
          </PageResultsProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
