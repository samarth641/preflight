"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Badge } from "@/components/ui/Badge"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { FlaskConical, FolderSearch, Cpu, Activity, TrendingUp, ChevronDown, ChevronUp, Target } from "lucide-react"
import { getDashboardStats, getRecentActivity, getHealth } from "@/lib/api"
import { formatRelativeTime } from "@/lib/utils"
import type { DashboardStats, ActivityItem } from "@/lib/types"
import Link from "next/link"

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [backendOnline, setBackendOnline] = useState(false)
  const [apiVersion, setApiVersion] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [activityExpanded, setActivityExpanded] = useState(false)

  useEffect(() => {
    Promise.all([getDashboardStats(), getRecentActivity(), getHealth().catch(() => null)])
      .then(([s, a, h]) => {
        setStats(s)
        setActivity(a)
        if (h?.status === "ok") {
          setBackendOnline(true)
          setApiVersion(h.version)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <FullSpinner label="Loading dashboard..." />

  // ─── Stat cards (bento 2×2) ───
  const statCards = [
    { label: "Total Analyses", value: stats?.total_experiments ?? 0, icon: FlaskConical, color: "var(--primary)" },
    { label: "Active Jobs", value: stats?.running ?? 0, icon: Activity, color: "var(--success)" },
    { label: "Avg Accuracy", value: stats?.avg_accuracy ? `${(stats.avg_accuracy * 100).toFixed(1)}%` : "—", icon: Target, color: "var(--info)" },
    { label: "Avg Savings", value: stats?.convergence_rate_percent != null ? `${stats.convergence_rate_percent.toFixed(1)}%` : "0%", icon: TrendingUp, color: "var(--warning)" },
  ]

  // ─── Quick actions ───
  const quickActions = [
    { href: "/analyze", label: "New Analysis", icon: FlaskConical, desc: "Predict cost, runtime, VRAM, convergence" },
    { href: "/dataset", label: "Analyze Dataset", icon: FolderSearch, desc: "Check dataset quality and readiness" },
    { href: "/gpu", label: "Find GPU", icon: Cpu, desc: "Get hardware recommendations" },
    { href: "/training", label: "Monitor Training", icon: Activity, desc: "Live training metrics and alerts" },
  ]

  return (
    <>
      <TopBar title="Dashboard" subtitle="Overview of your training intelligence" />
      <div className="dashboard-root">
        {/* ─── Top row: Bento 2×2 grid (left) + System Status (right) ─── */}
        <div className="dashboard-top-row">
          {/* Bento grid */}
          <div className="bento-grid">
            {statCards.map((card) => {
              const Icon = card.icon
              return (
                <div key={card.label} className="bento-card">
                  {/* Row 1: label (left) + icon (right, vertically centered) */}
                  <div className="bento-card-row">
                    <div className="bento-stat-label">{card.label}</div>
                    <div className="bento-stat-icon" style={{ color: card.color }}>
                      <Icon />
                    </div>
                  </div>
                  {/* Row 2: large value */}
                  <div className="bento-stat-value">{card.value}</div>
                </div>
              )
            })}
          </div>

          {/* System Status — matches bento grid height via fixed parent height */}
          <div className="system-status-card">
            <div className="system-status-title">System Status</div>
            <div className="system-status-list">
              <div className="system-status-row">
                <span className="system-status-label">Backend</span>
                <Badge variant={backendOnline ? "success" : "warning"}>
                  {backendOnline ? `Online v${apiVersion ?? ""}` : "Offline / Mock"}
                </Badge>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">ML Duration Predictor</span>
                <Badge variant="info">XGBoost v1</Badge>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">Benchmark Database</span>
                <span className="system-status-value">11 GPUs calibrated</span>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">Engine</span>
                <Badge variant="success">Rule-based</Badge>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">Rules Loaded</span>
                <span className="system-status-value">23</span>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">GPU Database</span>
                <span className="system-status-value">11 GPUs</span>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">Cloud Providers</span>
                <span className="system-status-value">6</span>
              </div>
              <div className="system-status-row">
                <span className="system-status-label">Version</span>
                <span className="system-status-value" style={{ color: "var(--text-muted)" }}>0.2.0</span>
              </div>
            </div>
          </div>
        </div>

        {/* ─── Quick Actions — section title + horizontal strip ─── */}
        <div className="section-title">Quick Actions</div>
        <div className="quick-actions-strip">
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.href}
                href={action.href}
                className="quick-action-btn"
              >
                <span className="quick-action-icon">
                  <Icon />
                </span>
                <div className="min-w-0">
                  <div className="quick-action-label">{action.label}</div>
                  <div className="quick-action-desc">{action.desc}</div>
                </div>
              </Link>
            )
          })}
        </div>

        {/* ─── Recent Activity — fills remaining viewport, internal scroll ─── */}
        <div className="recent-activity-container">
          <button
            className="recent-activity-toggle"
            onClick={() => setActivityExpanded(!activityExpanded)}
          >
            <span className="section-title">Recent Activity</span>
            <span className="recent-activity-meta">
              <span>{activity.length} entries{!activityExpanded && activity[0] ? ` · ${formatRelativeTime(activity[0].timestamp)}` : ""}</span>
              {activityExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </span>
          </button>
          <div className={`recent-activity-content ${activityExpanded ? "expanded" : ""}`}>
            <div className="recent-activity-list">
              {activity.length === 0 ? (
                <EmptyState title="No recent activity" description="Start an analysis or training job to see activity here." />
              ) : (
                activity.map((item) => {
                  const Icon = item.type === "analysis" ? FlaskConical : item.type === "dataset" ? FolderSearch : item.type === "gpu" ? Cpu : Activity
                  return (
                    <div key={item.id} className="recent-activity-item">
                      <div className="w-8 h-8 rounded-lg bg-[var(--bg)] flex items-center justify-center shrink-0">
                        <Icon className="w-4 h-4 text-[var(--text-secondary)]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="recent-activity-item-title">{item.title}</div>
                        <div className="recent-activity-item-desc">{item.description}</div>
                      </div>
                      <span className="recent-activity-item-time">{formatRelativeTime(item.timestamp)}</span>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
