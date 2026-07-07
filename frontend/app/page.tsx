"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { FlaskConical, FolderSearch, Cpu, Activity, TrendingUp, Database, Zap, DollarSign, Clock, Target } from "lucide-react"
import { getDashboardStats, getRecentActivity } from "@/lib/api"
import { formatUSD, formatRelativeTime } from "@/lib/utils"
import type { DashboardStats, ActivityItem } from "@/lib/types"
import Link from "next/link"

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboardStats(), getRecentActivity()])
      .then(([s, a]) => { setStats(s); setActivity(a) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <FullSpinner label="Loading dashboard..." />

  const statCards = [
    { label: "Total Analyses", value: stats?.total_analyses ?? 0, icon: FlaskConical, color: "var(--primary)" },
    { label: "Active Jobs", value: stats?.active_jobs ?? 0, icon: Activity, color: "var(--success)" },
    { label: "Datasets Analyzed", value: stats?.datasets_analyzed ?? 0, icon: Database, color: "var(--info)" },
    { label: "Avg Savings", value: `${stats?.avg_savings ?? 0}%`, icon: TrendingUp, color: "var(--warning)" },
  ]

  const quickActions = [
    { href: "/analyze", label: "New Analysis", icon: FlaskConical, desc: "Predict cost, runtime, VRAM, convergence" },
    { href: "/dataset", label: "Analyze Dataset", icon: FolderSearch, desc: "Check dataset quality and readiness" },
    { href: "/gpu", label: "Find GPU", icon: Cpu, desc: "Get hardware recommendations" },
    { href: "/training", label: "Monitor Training", icon: Activity, desc: "Live training metrics and alerts" },
  ]

  return (
    <>
      <TopBar title="Dashboard" subtitle="Overview of your training intelligence" />
      <div className="p-6 space-y-6">
        {/* Stat Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((card) => {
            const Icon = card.icon
            return (
              <Card key={card.label}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-1">{card.label}</p>
                    <p className="text-2xl font-bold text-[var(--text)] font-mono">{card.value}</p>
                  </div>
                  <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${card.color}15` }}>
                    <Icon className="w-5 h-5" style={{ color: card.color }} />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quick Actions */}
          <div className="lg:col-span-2">
            <Card title="Quick Actions">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {quickActions.map((action) => {
                  const Icon = action.icon
                  return (
                    <Link
                      key={action.href}
                      href={action.href}
                      className="flex items-center gap-4 p-4 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] hover:bg-[var(--surface-hover)] transition-colors"
                    >
                      <div className="w-10 h-10 rounded-lg bg-[var(--bg)] flex items-center justify-center shrink-0">
                        <Icon className="w-5 h-5 text-[var(--primary)]" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-[var(--text)]">{action.label}</div>
                        <div className="text-xs text-[var(--text-muted)] truncate">{action.desc}</div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            </Card>
          </div>

          {/* System Status */}
          <Card title="System Status">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">Backend</span>
                <Badge variant="warning">Mock Mode</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">Engine</span>
                <Badge variant="success">Rule-based</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">Rules Loaded</span>
                <span className="text-xs font-mono text-[var(--text)]">30</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">GPU Database</span>
                <span className="text-xs font-mono text-[var(--text)]">11 GPUs</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">Cloud Providers</span>
                <span className="text-xs font-mono text-[var(--text)]">6</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-secondary)]">Version</span>
                <span className="text-xs font-mono text-[var(--text-muted)]">0.1.0</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card title="Recent Activity">
          {activity.length === 0 ? (
            <EmptyState title="No recent activity" description="Start an analysis or training job to see activity here." />
          ) : (
            <div className="space-y-1">
              {activity.map((item) => {
                const Icon = item.type === "analysis" ? FlaskConical : item.type === "dataset" ? FolderSearch : item.type === "gpu" ? Cpu : Activity
                return (
                  <div key={item.id} className="flex items-center gap-3 py-3 border-b border-[var(--border)] last:border-0">
                    <div className="w-8 h-8 rounded-lg bg-[var(--bg)] flex items-center justify-center shrink-0">
                      <Icon className="w-4 h-4 text-[var(--text-secondary)]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-[var(--text)]">{item.title}</div>
                      <div className="text-xs text-[var(--text-muted)] truncate">{item.description}</div>
                    </div>
                    <span className="text-xs text-[var(--text-muted)] shrink-0">{formatRelativeTime(item.timestamp)}</span>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
