"use client"

import { useState, FormEvent } from "react"
import {
  FolderSearch,
  Upload,
  FileWarning,
  CheckCircle2,
  AlertTriangle,
  TrendingDown,
  Lightbulb,
  ExternalLink,
} from "lucide-react"

import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { NumberInput } from "@/components/ui/NumberInput"
import { Badge } from "@/components/ui/Badge"
import { Alert } from "@/components/ui/Alert"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ProgressBar } from "@/components/ui/ProgressBar"

import { gradeColor, confidencePercent, formatNumber } from "@/lib/utils"
import type { DatasetAnalysisResult, DatasetManualInput } from "@/lib/types"
import { analyzeDataset } from "@/lib/api"
import { usePageResults } from "@/components/providers/PageResultsContext"

type TabMode = "manual" | "path"

// ─── Metric Card helper ───

interface MetricItem {
  label: string
  value: string
}

function MetricCard({ label, value }: MetricItem) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-5">
      <p className="text-xs text-[var(--text-muted)] mb-2">{label}</p>
      <p className="text-lg font-mono font-semibold text-[var(--text)]">{value}</p>
    </div>
  )
}

// ─── Recommendation Card ───

function RecommendationItem({
  rec,
}: {
  rec: DatasetAnalysisResult["recommendations"][number]
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-5">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-start gap-2">
          <Lightbulb className="w-4 h-4 text-[var(--warning)] shrink-0 mt-0.5" />
          <div>
            <h4 className="text-sm font-medium text-[var(--text)]">{rec.title}</h4>
            <p className="text-xs text-[var(--text-secondary)] mt-1">{rec.recommendation}</p>
          </div>
        </div>
        <Badge variant="muted">{confidencePercent(rec.confidence)}</Badge>
      </div>

      <p className="text-xs text-[var(--text-muted)] mt-2 pl-6">
        <span className="text-[var(--text-secondary)]">Reason: </span>
        {rec.reason}
      </p>

      <div className="flex items-center gap-2 mt-3 pl-6">
        <span className="text-xs text-[var(--text-muted)]">Source: {rec.source}</span>
        {rec.documentation_url && (
          <a
            href={rec.documentation_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[var(--primary)] hover:underline"
          >
            <ExternalLink className="w-3 h-3" />
            Docs
          </a>
        )}
      </div>
    </div>
  )
}

// ─── Main Page ───

export default function DatasetPage() {
  const { dataset, setDataset } = usePageResults()
  const cached = dataset as { result: DatasetAnalysisResult | null; formState: Record<string, unknown> } | null

  const [mode, setMode] = useState<TabMode>("manual")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DatasetAnalysisResult | null>(cached?.result ?? null)

  // Manual entry form state
  const [imageCount, setImageCount] = useState((cached?.formState?.imageCount as number) ?? 5000)
  const [classCount, setClassCount] = useState((cached?.formState?.classCount as number) ?? 10)
  const [classImbalanceRatio, setClassImbalanceRatio] = useState((cached?.formState?.classImbalanceRatio as number) ?? 2.0)
  const [duplicatePercent, setDuplicatePercent] = useState((cached?.formState?.duplicatePercent as number) ?? 1.5)
  const [blurPercent, setBlurPercent] = useState((cached?.formState?.blurPercent as number) ?? 3.0)
  const [missingLabelPercent, setMissingLabelPercent] = useState((cached?.formState?.missingLabelPercent as number) ?? 2.0)
  const [medianResolution, setMedianResolution] = useState((cached?.formState?.medianResolution as number) ?? 512)

  // Path input state
  const [datasetPath, setDatasetPath] = useState("")

  async function handleManualSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const input: DatasetManualInput = {
        image_count: imageCount,
        class_count: classCount,
        class_imbalance_ratio: classImbalanceRatio,
        duplicate_percent: duplicatePercent,
        blur_percent: blurPercent,
        missing_label_percent: missingLabelPercent,
        median_resolution: medianResolution,
      }
      const res = await analyzeDataset(input)
      setResult(res)
      setDataset({ result: res, formState: { imageCount, classCount, classImbalanceRatio, duplicatePercent, blurPercent, missingLabelPercent, medianResolution } })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze dataset")
    } finally {
      setLoading(false)
    }
  }

  async function handlePathSubmit(e: FormEvent) {
    e.preventDefault()
    if (!datasetPath.trim()) {
      setError("Please enter a dataset path")
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeDataset({ path: datasetPath.trim() })
      setResult(res)
      setDataset({ result: res, formState: {} })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze dataset")
    } finally {
      setLoading(false)
    }
  }

  // ─── Render ───

  return (
    <div>
      <TopBar
        title="Dataset Intelligence"
        subtitle="Analyze dataset quality and predict training impact"
      />

      <div className="p-6 max-w-6xl mx-auto space-y-6">
        {/* ─── Input Section ─── */}
        <Card>
          {/* Tab toggle */}
          <div className="flex gap-1 mb-6 p-1 rounded-lg bg-[var(--bg)] border border-[var(--border)] w-fit">
            <button
              type="button"
              onClick={() => setMode("manual")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === "manual"
                  ? "bg-[var(--primary)] text-white"
                  : "text-[var(--text-secondary)] hover:text-[var(--text)]"
              }`}
            >
              Manual Entry
            </button>
            <button
              type="button"
              onClick={() => setMode("path")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === "path"
                  ? "bg-[var(--primary)] text-white"
                  : "text-[var(--text-secondary)] hover:text-[var(--text)]"
              }`}
            >
              Path Input
            </button>
          </div>

          {mode === "manual" ? (
            <form onSubmit={handleManualSubmit} className="space-y-5">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                <NumberInput
                  label="Image Count"
                  value={imageCount}
                  onChange={setImageCount}
                  min={0}
                  step={100}
                />
                <NumberInput
                  label="Class Count"
                  value={classCount}
                  onChange={setClassCount}
                  min={1}
                  step={1}
                />
                <NumberInput
                  label="Class Imbalance Ratio"
                  value={classImbalanceRatio}
                  onChange={setClassImbalanceRatio}
                  min={1}
                  step={0.1}
                />
                <NumberInput
                  label="Duplicate %"
                  value={duplicatePercent}
                  onChange={setDuplicatePercent}
                  min={0}
                  max={100}
                  step={0.1}
                />
                <NumberInput
                  label="Blur %"
                  value={blurPercent}
                  onChange={setBlurPercent}
                  min={0}
                  max={100}
                  step={0.1}
                />
                <NumberInput
                  label="Missing Label %"
                  value={missingLabelPercent}
                  onChange={setMissingLabelPercent}
                  min={0}
                  max={100}
                  step={0.1}
                />
                <NumberInput
                  label="Median Resolution"
                  value={medianResolution}
                  onChange={setMedianResolution}
                  min={1}
                  step={1}
                />
              </div>
              <div className="flex justify-end">
                <Button type="submit" loading={loading}>
                  <FolderSearch className="w-4 h-4" />
                  Analyze Dataset
                </Button>
              </div>
            </form>
          ) : (
            <form onSubmit={handlePathSubmit} className="space-y-5">
              <div>
                <label className="block text-xs text-[var(--text-secondary)] mb-1.5">
                  Dataset Path
                </label>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={datasetPath}
                    onChange={(e) => setDatasetPath(e.target.value)}
                    placeholder="/data/training/my_dataset"
                    className="flex-1 px-3 py-2.5 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--primary)] font-mono"
                  />
                  <Button type="submit" loading={loading}>
                    <Upload className="w-4 h-4" />
                    Analyze
                  </Button>
                </div>
                <p className="text-xs text-[var(--text-muted)] mt-2">
                  Enter the path to your image dataset directory. Analysis is simulated in this demo.
                </p>
              </div>
            </form>
          )}
        </Card>

        {/* ─── Error ─── */}
        {error && (
          <Alert severity="error" title="Analysis Failed">
            {error}
          </Alert>
        )}

        {/* ─── Loading ─── */}
        {loading && <FullSpinner label="Analyzing dataset..." />}

        {/* ─── Empty State ─── */}
        {!loading && !result && !error && (
          <Card>
            <EmptyState
              icon={<FolderSearch className="w-6 h-6 text-[var(--text-muted)]" />}
              title="No analysis yet"
              description="Enter dataset metrics manually or provide a path to analyze dataset quality, detect issues, and get recommendations."
            />
          </Card>
        )}

        {/* ─── Results ─── */}
        {!loading && result && (
          <div className="space-y-6">
            {/* Quality Score + Grade */}
            <Card>
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-1">Quality Score</p>
                    <p
                      className="text-6xl font-bold font-mono leading-none"
                      style={{ color: gradeColor(result.grade) }}
                    >
                      {result.score}
                    </p>
                  </div>
                  <div
                    className="flex items-center justify-center w-16 h-16 rounded-xl border-2 text-3xl font-bold"
                    style={{
                      color: gradeColor(result.grade),
                      borderColor: gradeColor(result.grade),
                      background: `${gradeColor(result.grade)}10`,
                    }}
                  >
                    {result.grade}
                  </div>
                </div>
                <div className="flex-1 w-full">
                  <ProgressBar
                    value={result.score}
                    max={100}
                    label="Overall Quality"
                    color={gradeColor(result.grade)}
                  />
                  <div className="flex items-center gap-2 mt-3">
                    {result.score >= 80 ? (
                      <CheckCircle2 className="w-4 h-4 text-[var(--success)]" />
                    ) : result.score >= 60 ? (
                      <AlertTriangle className="w-4 h-4 text-[var(--warning)]" />
                    ) : (
                      <FileWarning className="w-4 h-4 text-[var(--danger)]" />
                    )}
                    <span className="text-sm text-[var(--text-secondary)]">
                      {result.score >= 80
                        ? "Dataset quality is good — ready for training"
                        : result.score >= 60
                          ? "Dataset has issues that may affect training"
                          : "Dataset has critical issues — fix before training"}
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Warnings — right after quality score so issues are immediately visible */}
            {result.warnings.length > 0 && (
              <Card title="Warnings">
                <div className="space-y-3">
                  {result.warnings.map((w, i) => (
                    <Alert key={i} severity="warning" title={w.title}>
                      {w.message}
                    </Alert>
                  ))}
                </div>
              </Card>
            )}

            {/* Metrics Grid */}
            <Card title="Dataset Metrics">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                <MetricCard label="Image Count" value={formatNumber(result.metrics.image_count)} />
                <MetricCard label="Classes" value={formatNumber(result.metrics.class_count)} />
                <MetricCard
                  label="Imbalance Ratio"
                  value={`${result.metrics.class_imbalance_ratio.toFixed(1)}:1`}
                />
                <MetricCard
                  label="Duplicates"
                  value={`${result.metrics.duplicate_percent.toFixed(1)}%`}
                />
                <MetricCard label="Blur" value={`${result.metrics.blur_percent.toFixed(1)}%`} />
                <MetricCard
                  label="Missing Labels"
                  value={`${result.metrics.missing_label_percent.toFixed(1)}%`}
                />
                <MetricCard
                  label="Resolution (Min)"
                  value={`${formatNumber(result.metrics.min_resolution)}px`}
                />
                <MetricCard
                  label="Resolution (Median)"
                  value={`${formatNumber(result.metrics.median_resolution)}px`}
                />
                <MetricCard
                  label="Resolution (Avg)"
                  value={`${formatNumber(result.metrics.avg_resolution)}px`}
                />
                <MetricCard
                  label="Resolution (Max)"
                  value={`${formatNumber(result.metrics.max_resolution)}px`}
                />
              </div>
            </Card>

            {/* Accuracy Impact */}
            <Card title="Estimated Accuracy Impact">
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="w-8 h-8 text-[var(--danger)]" />
                    <div>
                      <p className="text-xs text-[var(--text-muted)]">Estimated Loss</p>
                      <p className="text-4xl font-bold font-mono text-[var(--danger)]">
                        {result.accuracy_impact.estimated_loss_percent.toFixed(1)}%
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 ml-auto">
                    <span className="text-xs text-[var(--text-muted)]">Confidence:</span>
                    <Badge variant="muted">
                      {confidencePercent(result.accuracy_impact.confidence)}
                    </Badge>
                  </div>
                </div>

                <div>
                  <p className="text-xs text-[var(--text-secondary)] mb-2">Contributing Factors</p>
                  <ul className="space-y-1.5">
                    {result.accuracy_impact.factors.map((factor, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-[var(--text-secondary)]"
                      >
                        <AlertTriangle className="w-3.5 h-3.5 text-[var(--warning)] shrink-0 mt-0.5" />
                        {factor}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>

            {/* Recommendations */}
            {result.recommendations.length > 0 && (
              <Card title="Recommendations">
                <div className="space-y-3">
                  {result.recommendations.map((rec) => (
                    <RecommendationItem key={rec.rule_id} rec={rec} />
                  ))}
                </div>
              </Card>
            )}

            {/* Sources */}
            {result.sources.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                <span>Sources:</span>
                {result.sources.map((src, i) => (
                  <Badge key={i} variant="muted">
                    {src}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
