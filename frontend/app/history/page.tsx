"use client"

import { useEffect, useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Badge } from "@/components/ui/Badge"
import { Button } from "@/components/ui/Button"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { Alert } from "@/components/ui/Alert"
import { History, Search, Eye, Trash2, ArrowLeft, CheckCircle2, XCircle, Square } from "lucide-react"
import { listExperiments, getExperiment, deleteExperiment } from "@/lib/api"
import { formatUSD, formatHours, formatPercent, formatRelativeTime, statusColor } from "@/lib/utils"
import type { Experiment, ExperimentDetail, ExperimentStatus } from "@/lib/types"

export default function HistoryPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [selected, setSelected] = useState<ExperimentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    listExperiments().then(setExperiments).finally(() => setLoading(false))
  }, [])

  const filtered = experiments.filter((e) => {
    if (statusFilter !== "all" && e.status !== statusFilter) return false
    if (search && !e.name.toLowerCase().includes(search.toLowerCase()) && !e.model.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const handleView = async (id: string) => {
    setDetailLoading(true)
    const detail = await getExperiment(id)
    setSelected(detail)
    setDetailLoading(false)
  }

  const handleDelete = async (id: string) => {
    await deleteExperiment(id)
    setExperiments(experiments.filter((e) => e.id !== id))
  }

  if (loading) return <FullSpinner label="Loading experiments..." />
  if (detailLoading) return <FullSpinner label="Loading experiment details..." />

  // Detail view
  if (selected) {
    const statusIcon = selected.status === "completed" ? CheckCircle2 : selected.status === "failed" ? XCircle : Square
    const StatusIcon = statusIcon
    return (
      <>
        <TopBar title="Experiment Details" subtitle={selected.name} />
        <div className="p-6 space-y-6">
          <Button variant="secondary" onClick={() => setSelected(null)}>
            <ArrowLeft className="w-4 h-4" /> Back to list
          </Button>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card title="Overview">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <StatusIcon className="w-4 h-4" style={{ color: statusColor(selected.status) }} />
                  <Badge variant={selected.status === "completed" ? "success" : selected.status === "failed" ? "danger" : "muted"}>
                    {selected.status}
                  </Badge>
                </div>
                {[
                  { label: "Model", value: selected.model },
                  { label: "Dataset", value: selected.dataset },
                  { label: "GPU", value: selected.gpu },
                  { label: "Date", value: new Date(selected.date).toLocaleString() },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">{row.label}</span>
                    <span className="text-[var(--text)] font-mono">{row.value}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Predictions vs Actuals">
              <div className="space-y-3">
                {[
                  { label: "Runtime", pred: formatHours(selected.predictions.estimated_runtime_hours), actual: formatHours(selected.actuals.runtime_hours) },
                  { label: "Cost", pred: formatUSD(selected.predictions.estimated_cost_usd), actual: formatUSD(selected.actuals.cost_usd) },
                  { label: "Accuracy", pred: `${formatPercent(selected.predictions.expected_accuracy_min, 0)}-${formatPercent(selected.predictions.expected_accuracy_max, 0)}`, actual: selected.actuals.accuracy ? formatPercent(selected.actuals.accuracy, 1) : "N/A" },
                  { label: "Converged", pred: `${formatPercent(selected.predictions.convergence_probability, 0)} likely`, actual: selected.actuals.converged ? "Yes" : "No" },
                ].map((row) => (
                  <div key={row.label} className="grid grid-cols-3 gap-2 text-sm">
                    <span className="text-[var(--text-muted)]">{row.label}</span>
                    <span className="text-[var(--text-secondary)] font-mono">Pred: {row.pred}</span>
                    <span className="text-[var(--text)] font-mono">Actual: {row.actual}</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card title="Recommendations Applied">
            <div className="space-y-2">
              {selected.recommendations_applied.map((rec, i) => (
                <div key={i} className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                  <CheckCircle2 className="w-4 h-4 text-[var(--success)]" /> {rec}
                </div>
              ))}
            </div>
          </Card>

          {selected.notes && (
            <Card title="Notes">
              <p className="text-sm text-[var(--text-secondary)]">{selected.notes}</p>
            </Card>
          )}
        </div>
      </>
    )
  }

  // List view
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
              {["all", "completed", "failed", "stopped", "running"].map((s) => (
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
                    <th className="text-right py-3 px-2 font-medium">Runtime</th>
                    <th className="text-right py-3 px-2 font-medium">Cost</th>
                    <th className="text-right py-3 px-2 font-medium">Accuracy</th>
                    <th className="text-left py-3 px-2 font-medium">Date</th>
                    <th className="text-right py-3 px-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((exp) => (
                    <tr key={exp.id} className="border-b border-[var(--border)] hover:bg-[var(--surface-hover)] transition-colors">
                      <td className="py-3 px-2 text-[var(--text)]">{exp.name}</td>
                      <td className="py-3 px-2 text-[var(--text-secondary)] font-mono text-xs">{exp.model}</td>
                      <td className="py-3 px-2 text-[var(--text-secondary)] text-xs">{exp.gpu}</td>
                      <td className="py-3 px-2">
                        <Badge variant={exp.status === "completed" ? "success" : exp.status === "failed" ? "danger" : exp.status === "running" ? "default" : "muted"}>
                          {exp.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 text-right text-[var(--text-secondary)] font-mono text-xs">{formatHours(exp.runtime_hours)}</td>
                      <td className="py-3 px-2 text-right text-[var(--text-secondary)] font-mono text-xs">{formatUSD(exp.cost_usd)}</td>
                      <td className="py-3 px-2 text-right text-[var(--text)] font-mono text-xs">{exp.accuracy ? formatPercent(exp.accuracy, 1) : "—"}</td>
                      <td className="py-3 px-2 text-[var(--text-muted)] text-xs">{formatRelativeTime(exp.date)}</td>
                      <td className="py-3 px-2">
                        <div className="flex justify-end gap-2">
                          <button onClick={() => handleView(exp.id)} className="p-1.5 rounded hover:bg-[var(--bg)] text-[var(--text-muted)] hover:text-[var(--primary)]">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(exp.id)} className="p-1.5 rounded hover:bg-[var(--bg)] text-[var(--text-muted)] hover:text-[var(--danger)]">
                            <Trash2 className="w-4 h-4" />
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
