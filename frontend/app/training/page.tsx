"use client"

import { useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Badge } from "@/components/ui/Badge"
import { Alert } from "@/components/ui/Alert"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ProgressBar } from "@/components/ui/ProgressBar"
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts"
import {
  Activity, Square, TrendingDown, TrendingUp, Cpu, MemoryStick,
  Zap, AlertTriangle, Lightbulb, Wifi,
} from "lucide-react"
import { startTraining, getTrainingMetrics, getTrainingHealth, stopTraining } from "@/lib/api"
import { gradeColor, confidencePercent, formatGB } from "@/lib/utils"
import type { EpochMetrics, TrainingAnalysisResult } from "@/lib/types"

// ─── Recharts dark theme helpers ───

const CHART_GRID = "var(--border)"
const CHART_TEXT = "var(--text-muted)"
const CHART_TOOLTIP_STYLE = {
  backgroundColor: "var(--surface)",
  border: `1px solid var(--border)`,
  borderRadius: "8px",
  color: "var(--text)",
  fontSize: "12px",
}
const CHART_TOOLTIP_ITEM = { color: "var(--text)" }
const CHART_TOOLTIP_LABEL = { color: "var(--text-muted)", marginBottom: "4px" }

// Chart colors
const COLOR_TRAIN_LOSS = "#3b82f6"
const COLOR_VAL_LOSS = "#f59e0b"
const COLOR_ACCURACY = "#22c55e"
const COLOR_GPU_UTIL = "#06b6d4"
const COLOR_VRAM = "#3b82f6"

const severityVariant: Record<string, "danger" | "warning" | "info"> = {
  high: "danger",
  medium: "warning",
  low: "info",
}

// ─── Custom tooltip for Recharts ───

function ChartTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string | number
}) {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div style={CHART_TOOLTIP_STYLE} className="px-3 py-2 shadow-lg">
      <div style={CHART_TOOLTIP_LABEL} className="text-xs">
        Epoch {label}
      </div>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="text-[var(--text-secondary)]">{entry.name}:</span>
          <span className="font-mono text-[var(--text)]">
            {typeof entry.value === "number" ? entry.value.toFixed(4) : entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}

// ─── Page ───

export default function TrainingPage() {
  const [jobIdInput, setJobIdInput] = useState("")
  const [connectedJobId, setConnectedJobId] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [loading, setLoading] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [epochData, setEpochData] = useState<EpochMetrics[] | null>(null)
  const [health, setHealth] = useState<TrainingAnalysisResult | null>(null)

  async function handleConnect() {
    if (!jobIdInput.trim()) {
      setError("Please enter a job ID or model name.")
      return
    }
    setError(null)
    setConnecting(true)
    try {
      // startTraining returns { job_id } — use it to fetch metrics + health
      const { job_id } = await startTraining({
        model: jobIdInput.trim(),
        dataset: "default",
        gpu: "auto",
      })
      setConnectedJobId(job_id)
      setConnecting(false)
      setLoading(true)
      const [metrics, analysis] = await Promise.all([
        getTrainingMetrics(job_id),
        getTrainingHealth(job_id),
      ])
      setEpochData(metrics)
      setHealth(analysis)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect to training job.")
    } finally {
      setConnecting(false)
      setLoading(false)
    }
  }

  async function handleStop() {
    if (!connectedJobId) return
    setStopping(true)
    try {
      await stopTraining(connectedJobId)
    } catch {
      // placeholder — ignore errors
    } finally {
      setStopping(false)
    }
  }

  function handleDisconnect() {
    setConnectedJobId(null)
    setEpochData(null)
    setHealth(null)
    setError(null)
    setJobIdInput("")
  }

  // ─── Loading state (connecting + fetching data) ───
  if (connecting || loading) {
    return (
      <>
        <TopBar title="Live Training Monitor" subtitle="Real-time metrics & health analysis" />
        <FullSpinner label={connecting ? "Connecting to training job..." : "Loading training metrics..."} />
      </>
    )
  }

  // ─── Empty state — no job connected ───
  if (!connectedJobId || !epochData || !health) {
    return (
      <>
        <TopBar title="Live Training Monitor" subtitle="Real-time metrics & health analysis" />
        <div className="p-6">
          {error && (
            <Alert severity="error" title="Connection Error" className="mb-6">
              {error}
            </Alert>
          )}
          {/* Connection form */}
          <Card title="Connect to Training Job" className="mb-6">
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={jobIdInput}
                onChange={(e) => setJobIdInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleConnect()}
                placeholder="Enter job ID or model name (e.g. llama-7b-lora)"
                className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--primary)] transition-colors"
              />
              <Button onClick={handleConnect} loading={connecting}>
                <Wifi className="w-4 h-4" />
                Connect
              </Button>
            </div>
          </Card>

          <EmptyState
            icon={<Activity className="w-6 h-6 text-[var(--text-muted)]" />}
            title="No training job connected"
            description="Enter a job ID or model name above and click Connect to start monitoring live training metrics, GPU utilization, and health analysis."
          />
        </div>
      </>
    )
  }

  // ─── Connected — full dashboard ───

  const m = health.metrics
  const latest = epochData[epochData.length - 1]
  const scoreColor = gradeColor(health.grade)

  // Prepare chart data — filter nulls per-chart via Recharts connectNulls={false}
  const lossData = epochData.map((e) => ({
    epoch: e.epoch,
    train_loss: e.train_loss,
    val_loss: e.val_loss,
  }))
  const accuracyData = epochData.map((e) => ({
    epoch: e.epoch,
    accuracy: e.accuracy !== null ? e.accuracy * 100 : null,
  }))
  const gpuData = epochData.map((e) => ({
    epoch: e.epoch,
    gpu_utilization: e.gpu_utilization,
  }))
  const vramData = epochData.map((e) => ({
    epoch: e.epoch,
    vram_gb: e.vram_gb,
  }))

  return (
    <>
      <TopBar title="Live Training Monitor" subtitle={`Job: ${connectedJobId}`} />

      <div className="p-6 space-y-6">
        {/* ─── Connection bar + controls ─── */}
        <Card>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--success)]/10 flex items-center justify-center">
                <Wifi className="w-5 h-5 text-[var(--success)]" />
              </div>
              <div>
                <div className="text-sm font-medium text-[var(--text)]">
                  Connected to <span className="font-mono">{connectedJobId}</span>
                </div>
                <div className="text-xs text-[var(--text-muted)]">
                  {epochData.length} epochs recorded
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="secondary" onClick={handleDisconnect}>
                Disconnect
              </Button>
              <Button variant="danger" onClick={handleStop} loading={stopping}>
                <Square className="w-4 h-4" />
                Stop Training
              </Button>
            </div>
          </div>
        </Card>

        {/* ─── Metrics summary bar ─── */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <SummaryStat
            icon={<Activity className="w-4 h-4" />}
            label="Current Epoch"
            value={`${m.current_epoch} / ${m.epoch_count}`}
            color="var(--primary)"
          />
          <SummaryStat
            icon={<TrendingDown className="w-4 h-4" />}
            label="Train Loss"
            value={m.latest_train_loss !== null ? m.latest_train_loss.toFixed(4) : "—"}
            color="var(--primary)"
          />
          <SummaryStat
            icon={<TrendingUp className="w-4 h-4" />}
            label="Val Loss"
            value={m.latest_val_loss !== null ? m.latest_val_loss.toFixed(4) : "—"}
            color="var(--warning)"
          />
          <SummaryStat
            icon={<Cpu className="w-4 h-4" />}
            label="GPU Util"
            value={m.gpu_utilization !== null ? `${m.gpu_utilization.toFixed(0)}%` : "—"}
            color="var(--info)"
          />
          <SummaryStat
            icon={<MemoryStick className="w-4 h-4" />}
            label="VRAM Usage"
            value={latest?.vram_gb !== null && latest?.vram_gb !== undefined ? formatGB(latest.vram_gb) : "—"}
            color="var(--primary)"
          />
        </div>

        {/* ─── Health score + warnings (sidebar row) ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Health score */}
          <Card title="Training Health Score">
            <div className="flex flex-col items-center justify-center py-2">
              <div
                className="text-5xl font-bold font-mono"
                style={{ color: scoreColor }}
              >
                {health.score}
              </div>
              <div
                className="text-2xl font-bold mt-1"
                style={{ color: scoreColor }}
              >
                Grade {health.grade}
              </div>
              <div className="w-full mt-4">
                <ProgressBar
                  value={health.score}
                  max={100}
                  label="Health Score"
                  color={scoreColor}
                  showValue={false}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2 justify-center">
                {m.overfitting_detected && (
                  <Badge variant="danger">Overfitting</Badge>
                )}
                {m.validation_loss_increasing && (
                  <Badge variant="warning">Val Loss Rising</Badge>
                )}
                {m.accuracy_plateau && (
                  <Badge variant="warning">Accuracy Plateau</Badge>
                )}
                {m.vram_near_limit && (
                  <Badge variant="danger">VRAM Near Limit</Badge>
                )}
                {m.train_loss_stagnant && (
                  <Badge variant="muted">Train Loss Stagnant</Badge>
                )}
                {!m.overfitting_detected && !m.validation_loss_increasing && !m.accuracy_plateau && (
                  <Badge variant="success">No Critical Issues</Badge>
                )}
              </div>
            </div>
          </Card>

          {/* Warnings */}
          <Card title="Warnings" className="lg:col-span-2">
            {health.warnings.length === 0 ? (
              <EmptyState
                icon={<Zap className="w-5 h-5 text-[var(--success)]" />}
                title="No warnings detected"
                description="Training is proceeding without any flagged issues."
              />
            ) : (
              <div className="space-y-3">
                {health.warnings.map((w, i) => (
                  <Alert key={i} severity="warning" title={w.title}>
                    {w.message}
                    <div className="mt-2 flex items-center gap-3 text-xs text-[var(--text-muted)]">
                      <span>Confidence: {confidencePercent(w.confidence)}</span>
                      <span>·</span>
                      <span>Source: {w.source}</span>
                    </div>
                  </Alert>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* ─── Charts: 2-column grid ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Loss Chart */}
          <Card title="Training & Validation Loss">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={lossData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
                <XAxis
                  dataKey="epoch"
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  label={{ value: "Epoch", position: "insideBottom", offset: -2, fill: CHART_TEXT, fontSize: 11 }}
                />
                <YAxis
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  domain={["auto", "auto"]}
                />
                <Tooltip content={<ChartTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: 11, color: CHART_TEXT }}
                  iconType="line"
                />
                <Line
                  type="monotone"
                  dataKey="train_loss"
                  name="Train Loss"
                  stroke={COLOR_TRAIN_LOSS}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="val_loss"
                  name="Val Loss"
                  stroke={COLOR_VAL_LOSS}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* Accuracy Chart */}
          <Card title="Accuracy">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={accuracyData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
                <XAxis
                  dataKey="epoch"
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  label={{ value: "Epoch", position: "insideBottom", offset: -2, fill: CHART_TEXT, fontSize: 11 }}
                />
                <YAxis
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  domain={[0, 100]}
                  unit="%"
                />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  name="Accuracy"
                  stroke={COLOR_ACCURACY}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  unit="%"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* GPU Utilization Chart */}
          <Card title="GPU Utilization">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={gpuData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
                <XAxis
                  dataKey="epoch"
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  label={{ value: "Epoch", position: "insideBottom", offset: -2, fill: CHART_TEXT, fontSize: 11 }}
                />
                <YAxis
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  domain={[0, 100]}
                  unit="%"
                />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="gpu_utilization"
                  name="GPU Utilization"
                  stroke={COLOR_GPU_UTIL}
                  strokeWidth={2}
                  dot={false}
                  connectNulls={false}
                  unit="%"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* VRAM Usage Chart (Area) */}
          <Card title="VRAM Usage">
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={vramData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="vramGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={COLOR_VRAM} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={COLOR_VRAM} stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={CHART_GRID} strokeDasharray="3 3" />
                <XAxis
                  dataKey="epoch"
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  label={{ value: "Epoch", position: "insideBottom", offset: -2, fill: CHART_TEXT, fontSize: 11 }}
                />
                <YAxis
                  stroke={CHART_TEXT}
                  tick={{ fill: CHART_TEXT, fontSize: 11 }}
                  domain={["auto", "auto"]}
                  unit=" GB"
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="vram_gb"
                  name="VRAM"
                  stroke={COLOR_VRAM}
                  strokeWidth={2}
                  fill="url(#vramGradient)"
                  dot={false}
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </div>

        {/* ─── Anomaly detection + Recommendations ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Anomaly Detection */}
          <Card
            title="Anomaly Detection"
            action={
              <span className="text-xs text-[var(--text-muted)]">
                {health.trends.length} trend{health.trends.length !== 1 ? "s" : ""} detected
              </span>
            }
          >
            {health.trends.length === 0 ? (
              <EmptyState
                icon={<AlertTriangle className="w-5 h-5 text-[var(--success)]" />}
                title="No anomalies detected"
                description="Training trends are within expected parameters."
              />
            ) : (
              <div className="space-y-3">
                {health.trends.map((trend, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                  >
                    <div className="shrink-0 mt-0.5">
                      <AlertTriangle
                        className="w-4 h-4"
                        style={{
                          color:
                            trend.severity === "high"
                              ? "var(--danger)"
                              : trend.severity === "medium"
                                ? "var(--warning)"
                                : "var(--info)",
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-[var(--text)]">
                          {trend.name}
                        </span>
                        <Badge variant={severityVariant[trend.severity]}>
                          {trend.severity}
                        </Badge>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] mb-2">
                        {trend.description}
                      </p>
                      <div className="text-xs text-[var(--text-muted)]">
                        Affected epochs:{" "}
                        <span className="font-mono">
                          {trend.epochs_affected.join(", ")}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Recommendations */}
          <Card
            title="Real-time Recommendations"
            action={
              <span className="text-xs text-[var(--text-muted)]">
                {health.recommendations.length} active
              </span>
            }
          >
            {health.recommendations.length === 0 ? (
              <EmptyState
                icon={<Lightbulb className="w-5 h-5 text-[var(--text-muted)]" />}
                title="No recommendations"
                description="No actionable recommendations at this time."
              />
            ) : (
              <div className="space-y-3">
                {health.recommendations.map((rec, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg border border-[var(--border)] bg-[var(--bg)]"
                  >
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <div className="flex items-center gap-2">
                        <Lightbulb className="w-4 h-4 text-[var(--warning)] shrink-0" />
                        <span className="text-sm font-medium text-[var(--text)]">
                          {rec.title}
                        </span>
                      </div>
                      <Badge variant="info">{confidencePercent(rec.confidence)}</Badge>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">
                      {rec.recommendation}
                    </p>
                    <div className="mt-2 flex items-center gap-2 text-xs text-[var(--text-muted)]">
                      <span className="px-1.5 py-0.5 rounded bg-[var(--surface-hover)] font-mono">
                        {rec.source}
                      </span>
                      <span>·</span>
                      <span>Priority {rec.priority}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* ─── Additional metrics detail ─── */}
        <Card title="Training Details">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            <DetailItem label="Best Val Loss" value={m.best_val_loss !== null ? m.best_val_loss.toFixed(4) : "—"} />
            <DetailItem label="Best Epoch" value={m.best_epoch !== null ? String(m.best_epoch) : "—"} />
            <DetailItem label="Overfitting Gap" value={m.overfitting_gap.toFixed(4)} />
            <DetailItem label="Avg GPU Util" value={m.avg_gpu_utilization !== null ? `${m.avg_gpu_utilization.toFixed(0)}%` : "—"} />
            <DetailItem label="CPU Utilization" value={m.cpu_utilization !== null ? `${m.cpu_utilization.toFixed(0)}%` : "—"} />
            <DetailItem label="VRAM Usage" value={m.vram_usage_percent !== null ? `${m.vram_usage_percent.toFixed(0)}%` : "—"} />
            <DetailItem label="Val Loss Increasing" value={m.validation_loss_increasing ? "Yes" : "No"} />
            <DetailItem label="Loss Diverging" value={m.loss_diverging ? "Yes" : "No"} />
          </div>
        </Card>
      </div>
    </>
  )
}

// ─── Sub-components ───

function SummaryStat({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-center gap-2 mb-2">
        <span style={{ color }}>{icon}</span>
        <span className="text-xs text-[var(--text-muted)]">{label}</span>
      </div>
      <p className="text-lg font-bold text-[var(--text)] font-mono">{value}</p>
    </div>
  )
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span className="text-sm font-mono text-[var(--text)]">{value}</span>
    </div>
  )
}
