"use client"

import { useState, useEffect, FormEvent } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Select } from "@/components/ui/Select"
import { NumberInput } from "@/components/ui/NumberInput"
import { Badge } from "@/components/ui/Badge"
import { Alert } from "@/components/ui/Alert"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { ProgressBar } from "@/components/ui/ProgressBar"
import { recommendGPU, listGPUBenchmarks } from "@/lib/api"
import { formatGB, fitRatingColor, confidencePercent } from "@/lib/utils"
import type {
  GPURecommendationRequest,
  GPURecommendationResult,
  GPUCandidate,
  FitRating,
  GPUBenchmark,
} from "@/lib/types"
import {
  Cpu,
  Zap,
  DollarSign,
  MemoryStick,
  Cloud,
  ExternalLink,
  AlertTriangle,
  Lightbulb,
  Gauge,
} from "lucide-react"

const fitRatingVariant: Record<FitRating, "success" | "default" | "warning" | "muted" | "danger"> = {
  excellent: "success",
  good: "default",
  tight: "warning",
  overkill: "muted",
  insufficient: "danger",
}

const trainingModeOptions = [
  { value: "full", label: "Full Training" },
  { value: "lora", label: "LoRA / Fine-tune" },
  { value: "inference", label: "Inference Only" },
]

const modelTypeOptions = [
  { value: "vision", label: "Vision Model" },
  { value: "cnn", label: "CNN" },
  { value: "transformer", label: "Transformer" },
]

const precisionOptions = [
  { value: "fp32", label: "FP32 (Full)" },
  { value: "fp16", label: "FP16 (Mixed)" },
  { value: "int8", label: "INT8 (Quantized)" },
]

const budgetTierOptions = [
  { value: "any", label: "Any Budget" },
  { value: "entry", label: "Entry (<$500)" },
  { value: "mid", label: "Mid ($500–$1K)" },
  { value: "high", label: "High ($1K–$3K)" },
  { value: "enthusiast", label: "Enthusiast ($3K+)" },
  { value: "datacenter", label: "Data Center" },
]

const vendorOptions = [
  { value: "any", label: "Any Vendor" },
  { value: "nvidia", label: "NVIDIA" },
  { value: "amd", label: "AMD" },
]

export default function GPURecommenderPage() {
  // ─── Form State ───
  const [parameterCount, setParameterCount] = useState(7)
  const [trainingMode, setTrainingMode] = useState("full")
  const [modelType, setModelType] = useState("transformer")
  const [precision, setPrecision] = useState("fp16")
  const [batchSize, setBatchSize] = useState(8)
  const [imageSize, setImageSize] = useState(224)
  const [sequenceLength, setSequenceLength] = useState(512)
  const [budgetTier, setBudgetTier] = useState("any")
  const [preferredVendor, setPreferredVendor] = useState("any")
  const [maxResults, setMaxResults] = useState(5)
  const [includeCloud, setIncludeCloud] = useState(true)

  // ─── Result State ───
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<GPURecommendationResult | null>(null)
  const [benchmarks, setBenchmarks] = useState<Record<string, GPUBenchmark>>({})

  useEffect(() => {
    listGPUBenchmarks().then(setBenchmarks)
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResult(null)

    const req: GPURecommendationRequest = {
      parameter_count_billion: parameterCount,
      training_mode: trainingMode as GPURecommendationRequest["training_mode"],
      model_type: modelType as GPURecommendationRequest["model_type"],
      precision: precision as GPURecommendationRequest["precision"],
      batch_size: batchSize,
      ...(modelType === "vision" && { image_size: imageSize }),
      ...(modelType === "transformer" && { sequence_length: sequenceLength }),
      ...(budgetTier !== "any" && { budget_tier: budgetTier as GPURecommendationRequest["budget_tier"] }),
      ...(preferredVendor !== "any" && { preferred_vendor: preferredVendor as GPURecommendationRequest["preferred_vendor"] }),
      max_results: maxResults,
      include_cloud: includeCloud,
    }

    try {
      const res = await recommendGPU(req)
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get GPU recommendations")
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <TopBar title="GPU Recommender" subtitle="Find the right GPU for your training workload" />
      <div className="p-6 space-y-6">
        {/* ─── Form ─── */}
        <Card title="Workload Parameters">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <NumberInput
                label="Parameter Count (B)"
                value={parameterCount}
                onChange={setParameterCount}
                step={0.5}
                min={0.1}
              />
              <Select
                label="Training Mode"
                value={trainingMode}
                onChange={setTrainingMode}
                options={trainingModeOptions}
              />
              <Select
                label="Model Type"
                value={modelType}
                onChange={setModelType}
                options={modelTypeOptions}
              />
              <Select
                label="Precision"
                value={precision}
                onChange={setPrecision}
                options={precisionOptions}
              />
              <NumberInput
                label="Batch Size"
                value={batchSize}
                onChange={setBatchSize}
                step={1}
                min={1}
              />
              {modelType === "vision" && (
                <NumberInput
                  label="Image Size (px)"
                  value={imageSize}
                  onChange={setImageSize}
                  step={32}
                  min={32}
                />
              )}
              {modelType === "transformer" && (
                <NumberInput
                  label="Sequence Length"
                  value={sequenceLength}
                  onChange={setSequenceLength}
                  step={128}
                  min={64}
                />
              )}
              <Select
                label="Budget Tier"
                value={budgetTier}
                onChange={setBudgetTier}
                options={budgetTierOptions}
              />
              <Select
                label="Preferred Vendor"
                value={preferredVendor}
                onChange={setPreferredVendor}
                options={vendorOptions}
              />
              <NumberInput
                label="Max Results"
                value={maxResults}
                onChange={setMaxResults}
                step={1}
                min={1}
                max={20}
              />
            </div>

            {/* Cloud checkbox */}
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={includeCloud}
                onChange={(e) => setIncludeCloud(e.target.checked)}
                className="w-4 h-4 rounded border-[var(--border)] bg-[var(--bg)] accent-[var(--primary)] cursor-pointer"
              />
              <span className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                <Cloud className="w-4 h-4" />
                Include cloud offerings
              </span>
            </label>

            <div className="flex justify-end">
              <Button type="submit" loading={loading} className="min-w-[160px]">
                <Cpu className="w-4 h-4" />
                Recommend GPUs
              </Button>
            </div>
          </form>
        </Card>

        {/* ─── Loading ─── */}
        {loading && <FullSpinner label="Analyzing workload and matching GPUs..." />}

        {/* ─── Error ─── */}
        {error && (
          <Alert severity="error" title="Recommendation Failed">
            {error}
          </Alert>
        )}

        {/* ─── Results ─── */}
        {result && !loading && !error && (
          <div className="space-y-6">
            {/* VRAM Requirement & Best Pick */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* VRAM Requirement */}
              <Card title="VRAM Requirement">
                <div className="flex flex-col items-center justify-center py-4">
                  <MemoryStick className="w-8 h-8 text-[var(--primary)] mb-3" />
                  <p className="text-3xl font-bold text-[var(--text)] font-mono">
                    {formatGB(result.required_vram_gb)}
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-2">
                    Minimum VRAM for your workload
                  </p>
                  <div className="w-full mt-4">
                    <ProgressBar
                      value={result.required_vram_gb}
                      max={80}
                      label="VRAM Requirement"
                      color="var(--primary)"
                      showValue={false}
                    />
                  </div>
                </div>
              </Card>

              {/* Best Pick */}
              <div className="lg:col-span-2">
                {result.best_pick ? (
                  <BestPickCard candidate={result.best_pick} requiredVram={result.required_vram_gb} benchmarks={benchmarks} />
                ) : (
                  <Card title="Best Pick">
                    <EmptyState
                      icon={<AlertTriangle className="w-6 h-6 text-[var(--warning)]" />}
                      title="No suitable GPU found"
                      description="Try adjusting your budget tier, vendor preference, or model parameters."
                    />
                  </Card>
                )}
              </div>
            </div>

            {/* GPU Candidates */}
            <Card title="Ranked GPU Candidates" action={<Badge variant="muted">{result.candidates.length} matches</Badge>}>
              {result.candidates.length === 0 ? (
                <EmptyState
                  icon={<Cpu className="w-6 h-6 text-[var(--text-muted)]" />}
                  title="No GPU candidates"
                  description="No GPUs matched your criteria. Try widening your filters."
                />
              ) : (
                <div className="space-y-3">
                  {result.candidates.map((candidate, idx) => (
                    <CandidateRow
                      key={candidate.gpu.id}
                      candidate={candidate}
                      rank={idx + 1}
                      requiredVram={result.required_vram_gb}
                      isBest={result.best_pick?.gpu.id === candidate.gpu.id}
                      benchmarks={benchmarks}
                    />
                  ))}
                </div>
              )}
            </Card>

            {/* Cloud Offerings */}
            {includeCloud && result.cloud_offerings.length > 0 && (
              <Card title="Cloud Offerings" action={<Cloud className="w-5 h-5 text-[var(--text-muted)]" />}>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-left">
                        <th className="py-2.5 pr-4 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Provider</th>
                        <th className="py-2.5 pr-4 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Instance</th>
                        <th className="py-2.5 pr-4 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">GPU</th>
                        <th className="py-2.5 pr-4 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide text-right">Count</th>
                        <th className="py-2.5 pr-4 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide text-right">VRAM</th>
                        <th className="py-2.5 text-xs font-medium text-[var(--text-muted)] uppercase tracking-wide">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.cloud_offerings.map((offering, idx) => (
                        <tr
                          key={`${offering.provider_id}-${offering.instance_type}-${idx}`}
                          className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-hover)] transition-colors"
                        >
                          <td className="py-3 pr-4">
                            <a
                              href={offering.provider_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[var(--primary)] hover:underline flex items-center gap-1"
                            >
                              {offering.provider_name}
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          </td>
                          <td className="py-3 pr-4 text-[var(--text)] font-mono text-xs">{offering.instance_type}</td>
                          <td className="py-3 pr-4 text-[var(--text-secondary)]">{offering.gpu_name}</td>
                          <td className="py-3 pr-4 text-[var(--text)] font-mono text-right">×{offering.gpu_count}</td>
                          <td className="py-3 pr-4 text-[var(--text)] font-mono text-right">{formatGB(offering.vram_gb)}</td>
                          <td className="py-3 text-xs text-[var(--text-muted)] max-w-xs">{offering.notes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            )}

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="space-y-3">
                {result.warnings.map((warning, idx) => (
                  <Alert key={warning.rule_id ?? idx} severity="warning" title={warning.title}>
                    {warning.message}
                    {warning.documentation_url && (
                      <a
                        href={warning.documentation_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-[var(--primary)] hover:underline ml-2"
                      >
                        Learn more <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </Alert>
                ))}
              </div>
            )}

            {/* Knowledge Recommendations */}
            {result.knowledge_recommendations.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-[var(--text)] mb-4 flex items-center gap-2">
                  <Lightbulb className="w-4 h-4 text-[var(--warning)]" />
                  Knowledge Recommendations
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {result.knowledge_recommendations.map((rec, idx) => {
                    const priorityVariant =
                      rec.priority >= 4 ? "danger" : rec.priority >= 3 ? "warning" : rec.priority >= 2 ? "default" : "muted"
                    const priorityLabel =
                      rec.priority >= 4 ? "Critical" : rec.priority >= 3 ? "High" : rec.priority >= 2 ? "Medium" : "Low"
                    return (
                      <Card key={rec.rule_id ?? idx}>
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <h4 className="text-sm font-medium text-[var(--text)] leading-tight">{rec.title}</h4>
                          <Badge variant={priorityVariant}>{priorityLabel}</Badge>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed mb-3">
                          {rec.recommendation}
                        </p>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-[var(--text-muted)]">Confidence</span>
                            <Badge variant="muted">{confidencePercent(rec.confidence)}</Badge>
                          </div>
                          {rec.documentation_url && (
                            <a
                              href={rec.documentation_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-[var(--primary)] hover:underline flex items-center gap-1"
                            >
                              {rec.source} <ExternalLink className="w-3 h-3" />
                            </a>
                          )}
                        </div>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Sources */}
            {result.sources.length > 0 && (
              <Card title="Sources">
                <div className="flex flex-wrap gap-2">
                  {result.sources.map((source, idx) => (
                    <Badge key={idx} variant="muted">{source}</Badge>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}

        {/* ─── Empty Initial State ─── */}
        {!result && !loading && !error && (
          <EmptyState
            icon={<Cpu className="w-6 h-6 text-[var(--text-muted)]" />}
            title="No recommendations yet"
            description="Configure your workload parameters above and click Recommend GPUs to get started."
          />
        )}
      </div>
    </>
  )
}

// ─── Best Pick Card ───

function BestPickCard({ candidate, requiredVram, benchmarks }: { candidate: GPUCandidate; requiredVram: number; benchmarks: Record<string, GPUBenchmark> }) {
  const { gpu, fit_rating, vram_utilization, headroom_gb, score } = candidate
  const benchmark = benchmarks[gpu.id]

  return (
    <div
      className="rounded-xl border-2 p-6"
      style={{
        borderColor: fitRatingColor(fit_rating),
        background: "var(--surface)",
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-lg flex items-center justify-center"
            style={{ background: `${fitRatingColor(fit_rating)}15` }}
          >
            <Cpu className="w-6 h-6" style={{ color: fitRatingColor(fit_rating) }} />
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="success">Best Pick</Badge>
              <Badge variant={fitRatingVariant[fit_rating]} className="capitalize">{fit_rating}</Badge>
            </div>
            <h3 className="text-lg font-semibold text-[var(--text)]">{gpu.name}</h3>
            <p className="text-xs text-[var(--text-muted)]">{gpu.vendor.toUpperCase()} · {gpu.architecture}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-[var(--text-muted)]">Match Score</p>
          <p className="text-2xl font-bold font-mono" style={{ color: fitRatingColor(fit_rating) }}>
            {score.toFixed(0)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <SpecItem icon={MemoryStick} label="VRAM" value={formatGB(gpu.vram_gb)} />
        <SpecItem icon={Zap} label="Bandwidth" value={`${gpu.memory_bandwidth_gbps} GB/s`} />
        <SpecItem icon={DollarSign} label="MSRP" value={gpu.msrp_usd ? `$${gpu.msrp_usd.toLocaleString()}` : "N/A"} />
        <SpecItem icon={Cpu} label="Power" value={`${gpu.power_watts}W`} />
      </div>

      {benchmark && (
        <div className="mb-4 p-3 rounded-lg bg-[var(--bg)] border border-[var(--border)]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Gauge className="w-4 h-4 text-[var(--info)]" />
              <span className="text-xs font-medium text-[var(--text)]">Benchmark Throughput</span>
              {!benchmark.approximate && <Badge variant="success">Measured</Badge>}
              {benchmark.approximate && <Badge variant="muted">Estimated</Badge>}
            </div>
            <span className="text-sm font-mono text-[var(--info)]">{benchmark.relative_training_throughput}x A100</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
            <span>MFU: ~{benchmark.typical_mfu_percent}%</span>
            <span className="truncate">Source: {benchmark.source}</span>
          </div>
        </div>
      )}

      <div className="space-y-3">
        <ProgressBar
          value={vram_utilization * 100}
          max={100}
          label="VRAM Utilization"
          color={fitRatingColor(fit_rating)}
        />
        <div className="flex items-center justify-between text-xs">
          <span className="text-[var(--text-muted)]">Headroom: <span className="text-[var(--text)] font-mono">{formatGB(headroom_gb)}</span></span>
          <span className="text-[var(--text-muted)]">Required: <span className="text-[var(--text)] font-mono">{formatGB(requiredVram)}</span></span>
        </div>
      </div>

      {candidate.reasons.length > 0 && (
        <div className="mt-4 pt-4 border-t border-[var(--border)]">
          <p className="text-xs text-[var(--text-muted)] mb-2">Why this GPU:</p>
          <ul className="space-y-1">
            {candidate.reasons.map((reason, idx) => (
              <li key={idx} className="text-xs text-[var(--text-secondary)] flex items-start gap-2">
                <span className="text-[var(--primary)] mt-0.5">▸</span>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ─── Candidate Row ───

function CandidateRow({
  candidate,
  rank,
  requiredVram,
  isBest,
  benchmarks,
}: {
  candidate: GPUCandidate
  rank: number
  requiredVram: number
  isBest: boolean
  benchmarks: Record<string, GPUBenchmark>
}) {
  const { gpu, fit_rating, score, vram_utilization, headroom_gb, reasons } = candidate
  const benchmark = benchmarks[gpu.id]

  return (
    <div
      className={`rounded-lg border p-4 transition-colors ${
        isBest
          ? "border-[var(--primary)] bg-[var(--primary)]/5"
          : "border-[var(--border)] hover:border-[var(--primary)]/50 hover:bg-[var(--surface-hover)]"
      }`}
    >
      <div className="flex items-start gap-4">
        {/* Rank */}
        <div className="w-8 h-8 rounded-lg bg-[var(--bg)] flex items-center justify-center shrink-0">
          <span className="text-sm font-mono font-bold text-[var(--text-muted)]">{rank}</span>
        </div>

        {/* GPU Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-[var(--text)]">{gpu.name}</span>
            {isBest && <Badge variant="success">Best Pick</Badge>}
            <Badge variant={fitRatingVariant[fit_rating]} className="capitalize">{fit_rating}</Badge>
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--text-muted)]">
            <span className="flex items-center gap-1"><MemoryStick className="w-3 h-3" /> {formatGB(gpu.vram_gb)}</span>
            <span className="flex items-center gap-1"><Zap className="w-3 h-3" /> {gpu.memory_bandwidth_gbps} GB/s</span>
            <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" /> {gpu.msrp_usd ? `$${gpu.msrp_usd.toLocaleString()}` : "N/A"}</span>
            <span className="flex items-center gap-1"><Cpu className="w-3 h-3" /> {gpu.vendor.toUpperCase()}</span>
            {benchmark && (
              <span className="flex items-center gap-1 text-[var(--info)]">
                <Gauge className="w-3 h-3" /> {benchmark.relative_training_throughput}x A100
                {!benchmark.approximate && <Badge variant="success" className="ml-1">Measured</Badge>}
              </span>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="text-right shrink-0">
          <p className="text-lg font-bold font-mono" style={{ color: fitRatingColor(fit_rating) }}>
            {score.toFixed(0)}
          </p>
          <p className="text-xs text-[var(--text-muted)]">score</p>
        </div>
      </div>

      {/* VRAM Bar */}
      <div className="mt-3 ml-12">
        <ProgressBar
          value={vram_utilization * 100}
          max={100}
          label={`${formatGB(requiredVram)} needed → ${formatGB(gpu.vram_gb)} available`}
          color={fitRatingColor(fit_rating)}
          showValue={false}
        />
        <div className="flex items-center justify-between text-xs mt-1.5">
          <span className="text-[var(--text-muted)]">Headroom: <span className="text-[var(--text)] font-mono">{formatGB(headroom_gb)}</span></span>
          <span className="text-[var(--text-muted)]">Util: <span className="text-[var(--text)] font-mono">{(vram_utilization * 100).toFixed(0)}%</span></span>
        </div>
      </div>

      {/* Reasons */}
      {reasons.length > 0 && (
        <div className="mt-2 ml-12 flex flex-wrap gap-1.5">
          {reasons.slice(0, 3).map((reason, idx) => (
            <span key={idx} className="text-xs text-[var(--text-muted)] bg-[var(--bg)] px-2 py-0.5 rounded">
              {reason}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Spec Item ───

function SpecItem({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) {
  return (
    <div>
      <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] mb-1">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <p className="text-sm font-mono text-[var(--text)]">{value}</p>
    </div>
  )
}
