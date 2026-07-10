"use client"

import { useState, useEffect } from "react"
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
import { DollarSign, Clock, Gauge, Cpu, Info } from "lucide-react"
import { predictDuration, listGPUs, listGPUBenchmarks } from "@/lib/api"
import { formatUSD } from "@/lib/utils"
import { usePageResults } from "@/components/providers/PageResultsContext"
import type { DurationPredictResult, GPUSpec, GPUBenchmark, Domain } from "@/lib/types"

const domainOptions = [
  { value: "language", label: "Language / LLM" },
  { value: "vision", label: "Vision" },
  { value: "multimodal", label: "Multimodal" },
  { value: "image generation", label: "Image Generation" },
  { value: "biology", label: "Biology" },
  { value: "other", label: "Other" },
]

const cloudProviderOptions = [
  { value: "none", label: "No cost estimate" },
  { value: "azure", label: "Microsoft Azure (AMD MI300X+ + NVIDIA)" },
  { value: "tensorwave", label: "TensorWave (AMD)" },
  { value: "digitalocean", label: "DigitalOcean (AMD MI300X + NVIDIA)" },
  { value: "runpod", label: "RunPod (NVIDIA + AMD)" },
  { value: "vast", label: "Vast.ai (NVIDIA + AMD)" },
  { value: "salad", label: "SaladCloud (consumer NVIDIA)" },
  { value: "coreweave", label: "CoreWeave (NVIDIA)" },
  { value: "aws", label: "AWS (NVIDIA)" },
  { value: "gcp", label: "Google Cloud (NVIDIA)" },
  { value: "lambda", label: "Lambda Labs (NVIDIA)" },
]

export default function MLDurationPage() {
  const { mlDuration, setMLDuration } = usePageResults()

  // Restore from context if available
  const cached = mlDuration as { result: DurationPredictResult | null; formState: Record<string, unknown> } | null

  const [durationResult, setDurationResult] = useState<DurationPredictResult | null>(cached?.result ?? null)
  const [durationLoading, setDurationLoading] = useState(false)
  const [durationError, setDurationError] = useState<string | null>(null)

  const [gpus, setGpus] = useState<GPUSpec[]>([])
  const [benchmarks, setBenchmarks] = useState<Record<string, GPUBenchmark>>({})

  const [durationParams, setDurationParams] = useState((cached?.formState?.durationParams as number) ?? 7.1)
  const [datasetTokens, setDatasetTokens] = useState((cached?.formState?.datasetTokens as number) ?? 2000000)
  const [gpuId, setGpuId] = useState((cached?.formState?.gpuId as string) ?? "mi300x")
  const [nGpus, setNGpus] = useState((cached?.formState?.nGpus as number) ?? 1)
  const [durationEpochs, setDurationEpochs] = useState((cached?.formState?.durationEpochs as number) ?? 3)
  const [domain, setDomain] = useState<Domain>("language")
  const [cloudProvider, setCloudProvider] = useState("azure")

  useEffect(() => {
    listGPUs().then(setGpus)
    listGPUBenchmarks().then(setBenchmarks)
  }, [])

  const handlePredictDuration = async () => {
    setDurationLoading(true)
    setDurationError(null)
    try {
      const result = await predictDuration({
        parameter_count_billion: durationParams,
        dataset_tokens: datasetTokens,
        gpu_id: gpuId,
        n_gpus: nGpus,
        epochs: durationEpochs,
        domain,
        cloud_provider: cloudProvider === "none" ? null : cloudProvider,
      })
      setDurationResult(result)
      // Persist to context so navigating away and back preserves results
      setMLDuration({
        result,
        formState: { durationParams, datasetTokens, gpuId, nGpus, durationEpochs, domain, cloudProvider },
      })
    } catch (err) {
      setDurationError(err instanceof Error ? err.message : "Duration prediction failed")
    } finally {
      setDurationLoading(false)
    }
  }

  const selectedBenchmark = benchmarks[gpuId]
  const gpuOptions = gpus.map(g => ({ value: g.id, label: g.name }))

  return (
    <>
      <TopBar title="ML Duration Prediction" subtitle="XGBoost-powered training time estimation" />
      <div className="p-6 space-y-6">
        <Card title="ML Duration Prediction" action={<Badge variant="info">XGBoost v1</Badge>}>
          <div className="space-y-4">
            <div className="flex items-start gap-2 text-xs text-[var(--text-muted)] bg-[var(--bg)] rounded-lg p-3">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>Backend endpoint: <code className="text-[var(--text-secondary)]">POST /api/v1/predict/duration</code>. Uses an XGBoost model trained on MLPerf + benchmark data. Falls back to physics formula (6ND rule) if the model artifact is unavailable.</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <NumberInput label="Parameters (B)" value={durationParams} onChange={setDurationParams} step={0.1} min={0.01} />
              <NumberInput label="Dataset Tokens" value={datasetTokens} onChange={setDatasetTokens} step={100000} min={1} />
              <Select label="GPU" value={gpuId} onChange={setGpuId} options={gpuOptions} />
              <NumberInput label="GPU Count" value={nGpus} onChange={setNGpus} min={1} />
              <NumberInput label="Epochs" value={durationEpochs} onChange={setDurationEpochs} min={1} />
              <Select label="Domain" value={domain} onChange={(v) => setDomain(v as Domain)} options={domainOptions} />
              <Select label="Cloud Provider" value={cloudProvider} onChange={setCloudProvider} options={cloudProviderOptions} />
            </div>
            {selectedBenchmark && (
              <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                <Gauge className="w-4 h-4" />
                <span>Benchmark: <span className="text-[var(--text-secondary)] font-mono">{selectedBenchmark.relative_training_throughput}x A100</span> throughput · MFU ~{selectedBenchmark.typical_mfu_percent}% · {selectedBenchmark.source}</span>
              </div>
            )}
            <div className="flex gap-3">
              <Button onClick={handlePredictDuration} loading={durationLoading}>
                <Clock className="w-4 h-4" /> Predict Duration
              </Button>
            </div>
          </div>
        </Card>

        {durationError && <Alert severity="error" title="Duration Prediction Failed">{durationError}</Alert>}
        {durationLoading && <FullSpinner label="Running ML duration prediction..." />}

        {durationResult && !durationLoading && (
          <div className="space-y-4">
            <Card title="Duration Prediction Results" action={<Badge variant="success">{durationResult.model_version}</Badge>}>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                <div className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4" style={{ color: "var(--primary)" }} />
                    <span className="text-xs text-[var(--text-muted)]">Est. Duration</span>
                  </div>
                  <p className="text-2xl font-bold font-mono leading-tight" style={{ color: "var(--primary)" }}>{durationResult.estimated_duration_human}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-2">{durationResult.estimated_hours.toFixed(2)} hours</p>
                </div>
                <div className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-3">
                    <Gauge className="w-4 h-4" style={{ color: "var(--info)" }} />
                    <span className="text-xs text-[var(--text-muted)]">Theoretical</span>
                  </div>
                  <p className="text-xl font-semibold font-mono" style={{ color: "var(--info)" }}>{durationResult.theoretical_hours.toFixed(2)}h</p>
                  <p className="text-xs text-[var(--text-muted)] mt-2">Physics formula (6ND)</p>
                </div>
                <div className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-3">
                    <Cpu className="w-4 h-4" style={{ color: "var(--text-secondary)" }} />
                    <span className="text-xs text-[var(--text-muted)]">GPU</span>
                  </div>
                  <p className="text-xl font-semibold font-mono text-[var(--text)]">{durationResult.gpu_id}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-2">×{durationResult.n_gpus}</p>
                </div>
                {durationResult.estimated_cost_usd !== null ? (
                  <div className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="w-4 h-4" style={{ color: "var(--success)" }} />
                      <span className="text-xs text-[var(--text-muted)]">Est. Cost</span>
                    </div>
                    <p className="text-2xl font-bold font-mono leading-tight" style={{ color: "var(--success)" }}>{formatUSD(durationResult.estimated_cost_usd)}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-2">@ {formatUSD(durationResult.hourly_rate_usd || 0)}/h · {durationResult.cost_provider}</p>
                  </div>
                ) : (
                  <div className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="w-4 h-4 text-[var(--text-muted)]" />
                      <span className="text-xs text-[var(--text-muted)]">Est. Cost</span>
                    </div>
                    <p className="text-xl font-semibold font-mono text-[var(--text-muted)]">N/A</p>
                    <p className="text-xs text-[var(--text-muted)] mt-2">Select a cloud provider</p>
                  </div>
                )}
              </div>

              {durationResult.theoretical_hours > 0 && (
                <div className="mt-5">
                  <div className="text-xs font-medium text-[var(--text-secondary)] mb-3">ML Prediction vs Physics Formula</div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[var(--text-secondary)] w-24">ML (XGBoost)</span>
                      <div className="flex-1">
                        <ProgressBar value={durationResult.estimated_hours} max={Math.max(durationResult.estimated_hours, durationResult.theoretical_hours) * 1.2} color="var(--primary)" showValue={false} />
                      </div>
                      <span className="text-xs font-mono text-[var(--text)] w-16 text-right">{durationResult.estimated_hours.toFixed(2)}h</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[var(--text-secondary)] w-24">Physics (6ND)</span>
                      <div className="flex-1">
                        <ProgressBar value={durationResult.theoretical_hours} max={Math.max(durationResult.estimated_hours, durationResult.theoretical_hours) * 1.2} color="var(--info)" showValue={false} />
                      </div>
                      <span className="text-xs font-mono text-[var(--text)] w-16 text-right">{durationResult.theoretical_hours.toFixed(2)}h</span>
                    </div>
                  </div>
                  <div className="mt-3 text-xs text-[var(--text-muted)]">
                    ML prediction is {durationResult.estimated_hours < durationResult.theoretical_hours
                      ? `${((1 - durationResult.estimated_hours / durationResult.theoretical_hours) * 100).toFixed(0)}% faster than`
                      : `${((durationResult.estimated_hours / durationResult.theoretical_hours - 1) * 100).toFixed(0)}% slower than`
                    } the physics formula.
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}

        {!durationResult && !durationLoading && !durationError && (
          <Card>
            <EmptyState
              icon={<Clock className="w-6 h-6 text-[var(--text-muted)]" />}
              title="No prediction yet"
              description="Configure your parameters above and click Predict Duration to estimate training time using the XGBoost ML model."
            />
          </Card>
        )}
      </div>
    </>
  )
}
