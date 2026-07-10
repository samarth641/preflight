"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { History, Search, Eye, ArrowLeft, CheckCircle2, XCircle, Square } from "lucide-react"
import { listExperiments } from "@/lib/api"
import { formatRelativeTime } from "@/lib/utils"
import type { ExperimentRecord, ExperimentHistoryResponse } from "@/lib/types"

export default function HistoryPage() {
  const [data, setData] = useState<ExperimentHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selected, setSelected] = useState<ExperimentRecord | null>(null)

  useEffect(() => {
    listExperiments().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <FullSpinner label="Loading experiments..." />

  const experiments = data?.experiments ?? []

  const filtered = experiments.filter((e) => {
    if (statusFilter !== "all" && e.status !== statusFilter) return false
    if (search && !e.name.toLowerCase().includes(search.toLowerCase()) && !e.model.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  // ─── Detail view ───
  if (selected) {
    const statusIcon = selected.status === "completed" ? CheckCircle2 : selected.status === "failed" ? XCircle : Square
    const StatusIcon = statusIcon
    return (
      <>
        <TopBar title="Experiment Details" subtitle={selected.name} />
        <div className="p-6 space-y-6">
          <button
            onClick={() => setSelected(null)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--surface-hover)] text-[var(--text-secondary)] hover:text-[var(--text)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to list
          </button>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Overview">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <StatusIcon className="w-4 h-4" style={{ color: selected.status === "completed" ? "var(--success)" : selected.status === "failed" ? "var(--danger)" : "var(--primary)" }} />
                  <Badge variant={selected.status === "completed" ? "success" : selected.status === "failed" ? "danger" : "default"}>
                    {selected.status}
                  </Badge>
                </div>
                {[
                  { label: "Model", value: selected.model },
                  { label: "Dataset", value: selected.dataset },
                  { label: "GPU", value: selected.gpu },
                  { label: "Parameters", value: `${(selected.params_million / 1000).toFixed(1)}B` },
                  { label: "Started", value: new Date(selected.started_at).toLocaleString() },
                  { label: "Duration", value: selected.duration_hours != null ? `${selected.duration_hours.toFixed(1)}h` : "—" },
                  { label: "Convergence", value: selected.convergence ?? "—" },
                  { label: "Target Accuracy", value: selected.target_accuracy != null ? `${(selected.target_accuracy * 100).toFixed(0)}%` : "—" },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">{row.label}</span>
                    <span className="text-[var(--text)] font-mono">{row.value}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Training Progress">
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-1">Epochs</p>
                    <p className="text-2xl font-bold font-mono text-[var(--text)]">
                      {selected.epochs_completed} / {selected.total_epochs}
                    </p>
                  </div>
                </div>
                <div className="w-full bg-[var(--bg)] rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(selected.epochs_completed / selected.total_epochs) * 100}%`,
                      background: selected.status === "completed" ? "var(--success)" : selected.status === "failed" ? "var(--danger)" : "var(--primary)",
                    }}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-1">Final Accuracy</p>
                    <p className="text-lg font-mono text-[var(--text)]">
                      {selected.final_accuracy != null ? `${(selected.final_accuracy * 100).toFixed(1)}%` : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-1">Best Val Loss</p>
                    <p className="text-lg font-mono text-[var(--text)]">
                      {selected.best_val_loss != null ? selected.best_val_loss.toFixed(4) : "—"}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </>
    )
  }

  // ─── List view ───
  return (
    <>
      <TopBar title="Experiment History" subtitle="Browse and learn from past training runs" />
      <div className="p-6 space-y-6">
        {/* Filters */}
        <Card>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search by name or model..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)]"
              />
            </div>
            <div className="flex gap-2">
              {["all", "running", "completed", "failed"].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    statusFilter === s
                      ? "bg-[var(--primary)] text-white"
                      : "bg-[var(--bg)] text-[var(--text-secondary)] border border-[var(--border)] hover:border-[var(--primary)]"
                  }`}
                >
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* Table */}
        <Card>
          {filtered.length === 0 ? (
            <EmptyState
              icon={<History className="w-6 h-6 text-[var(--text-muted)]" />}
              title="No experiments found"
              description="Run an analysis and start a training job to see experiments here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-xs text-[var(--text-muted)]">
                    <th className="text-left py-3 px-2 font-medium">Name</th>
                    <th className="text-left py-3 px-2 font-medium">Model</th>
                    <th className="text-left py-3 px-2 font-medium">GPU</th>
                    <th className="text-left py-3 px-2 font-medium">Status</th>
                    <th className="text-right py-3 px-2 font-medium">Epochs</th>
                    <th className="text-right py-3 px-2 font-medium">Accuracy</th>
                    <th className="text-left py-3 px-2 font-medium">Convergence</th>
                    <th className="text-left py-3 px-2 font-medium">Started</th>
                    <th className="text-right py-3 px-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((exp) => (
                    <tr key={exp.id} className="border-b border-[var(--border)] hover:bg-[var(--surface-hover)] transition-colors cursor-pointer" onClick={() => setSelected(exp)}>
                      <td className="py-3 px-2 text-[var(--text)]">{exp.name}</td>
                      <td className="py-3 px-2 text-[var(--text-secondary)] font-mono text-xs">{exp.model}</td>
                      <td className="py-3 px-2 text-[var(--text-secondary)] text-xs">{exp.gpu}</td>
                      <td className="py-3 px-2">
                        <Badge variant={exp.status === "completed" ? "success" : exp.status === "failed" ? "danger" : exp.status === "running" ? "default" : "muted"}>
                          {exp.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 text-right text-[var(--text-secondary)] font-mono text-xs">
                        {exp.epochs_completed}/{exp.total_epochs}
                      </td>
                      <td className="py-3 px-2 text-right text-[var(--text)] font-mono text-xs">
                        {exp.final_accuracy != null ? `${(exp.final_accuracy * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-3 px-2 text-[var(--text-muted)] text-xs">{exp.convergence ?? "—"}</td>
                      <td className="py-3 px-2 text-[var(--text-muted)] text-xs">{formatRelativeTime(exp.started_at)}</td>
                      <td className="py-3 px-2">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={(e) => { e.stopPropagation(); setSelected(exp) }}
                            className="p-1.5 rounded hover:bg-[var(--bg)] text-[var(--text-muted)] hover:text-[var(--primary)]"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  )
}
