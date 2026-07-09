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
import { DollarSign, Clock, MemoryStick, AlertTriangle, Target, Cpu, Leaf, Zap, Lightbulb, CheckSquare, FlaskConical, Gauge, TrendingDown, Info } from "lucide-react"
import { analyzeTraining, predictDuration, listGPUs, listGPUBenchmarks } from "@/lib/api"
import { formatUSD, formatHours, formatGB, formatPercent, confidencePercent } from "@/lib/utils"
import type { AnalysisResult, AnalysisRequest, ModelType, TrainingMode, Precision, DurationPredictResult, GPUSpec, GPUBenchmark, Domain } from "@/lib/types"

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
  { value: "aws", label: "AWS" },
  { value: "gcp", label: "Google Cloud" },
  { value: "azure", label: "Microsoft Azure" },
  { value: "lambda", label: "Lambda Labs" },
  { value: "runpod", label: "RunPod" },
  { value: "vast", label: "Vast.ai" },
]

export default function AnalyzePage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Duration prediction state
  const [durationResult, setDurationResult] = useState<DurationPredictResult | null>(null)
  const [durationLoading, setDurationLoading] = useState(false)
  const [durationError, setDurationError] = useState<string | null>(null)

  // GPU list for selector
  const [gpus, setGpus] = useState<GPUSpec[]>([])
  const [benchmarks, setBenchmarks] = useState<Record<string, GPUBenchmark>>({})

  // Form state — existing analysis
  const [modelType, setModelType] = useState<ModelType>("transformer")
  const [params, setParams] = useState(7)
  const [mode, setMode] = useState<TrainingMode>("lora")
  const [precision, setPrecision] = useState<Precision>("fp16")
  const [batchSize, setBatchSize] = useState(4)
  const [lr, setLr] = useState(0.001)
  const [optimizer, setOptimizer] = useState("adamw")
  const [scheduler, setScheduler] = useState("cosine")
  const [epochs, setEpochs] = useState(3)
  const [seqLen, setSeqLen] = useState(512)
  const [imgSize, setImgSize] = useState(224)
  const [datasetSize, setDatasetSize] = useState(2000000)

  // Form state — duration prediction
  const [durationParams, setDurationParams] = useState(7)
  const [datasetTokens, setDatasetTokens] = useState(2000000)
  const [gpuId, setGpuId] = useState("mi300x")
  const [nGpus, setNGpus] = useState(1)
  const [durationEpochs, setDurationEpochs] = useState(3)
  const [domain, setDomain] = useState<Domain>("language")
  const [cloudProvider, setCloudProvider] = useState("azure")

  useEffect(() => {
    listGPUs().then(setGpus)
    listGPUBenchmarks().then(setBenchmarks)
  }, [])

  const handleAnalyze = async () => {
    setLoading(true)
    setError(null)
    try {
      const req: AnalysisRequest = {
        model_type: modelType,
        parameter_count_billion: params,
        training_mode: mode,
        precision,
        batch_size: batchSize,
        learning_rate: lr,
        optimizer,
        scheduler,
        epochs,
        sequence_length: modelType === "transformer" ? seqLen : undefined,
        image_size: modelType === "vision" ? imgSize : undefined,
        dataset_size: datasetSize,
      }
      const data = await analyzeTraining(req)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed")
    } finally {
      setLoading(false)
    }
  }

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
    } catch (err) {
      setDurationError(err instanceof Error ? err.message : "Duration prediction failed")
    } finally {
      setDurationLoading(false)
    }
  }

  if (loading) return <FullSpinner label="Analyzing training configuration..." />

  const predictions = result?.predictions
  const predictionCards = predictions ? [
    { label: "Est. Cost", value: formatUSD(predictions.estimated_cost_usd), icon: DollarSign, color: "var(--success)" },
    { label: "Est. Runtime", value: formatHours(predictions.estimated_runtime_hours), icon: Clock, color: "var(--primary)" },
    { label: "Peak VRAM", value: formatGB(predictions.peak_vram_gb), icon: MemoryStick, color: "var(--info)" },
    { label: "OOM Risk", value: formatPercent(predictions.oom_probability), icon: AlertTriangle, color: predictions.oom_probability > 0.3 ? "var(--danger)" : "var(--success)" },
    { label: "Convergence", value: formatPercent(predictions.convergence_probability), icon: Target, color: predictions.convergence_probability > 0.7 ? "var(--success)" : "var(--warning)" },
    { label: "Accuracy Range", value: `${formatPercent(predictions.expected_accuracy_min, 0)}-${formatPercent(predictions.expected_accuracy_max, 0)}`, icon: Target, color: "var(--primary)" },
    { label: "GPU Utilization", value: formatPercent(predictions.gpu_utilization_estimate), icon: Cpu, color: "var(--info)" },
    { label: "Carbon", value: `${predictions.carbon_footprint_kg.toFixed(1)} kg CO₂e`, icon: Leaf, color: "var(--text-muted)" },
  ] : []

  const selectedBenchmark = benchmarks[gpuId]
  const gpuOptions = gpus.map(g => ({ value: g.id, label: g.name }))

  return (
    <>
      <TopBar title="Pre-Training Analysis" subtitle="Predict outcomes before allocating GPU resources" />
      <div className="p-6 space-y-6">
        {/* ML Duration Prediction */}
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

        {/* Duration Prediction Results */}
        {durationError && <Alert severity="error" title="Duration Prediction Failed">{durationError}</Alert>}

        {durationLoading && <FullSpinner label="Running ML duration prediction..." />}

        {durationResult && !durationLoading && (
          <div className="space-y-4">
            {/* Duration Prediction Cards */}
            <Card title="Duration Prediction Results" action={<Badge variant="success">{durationResult.model_version}</Badge>}>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-4 h-4" style={{ color: "var(--primary)" }} />
                    <span className="text-xs text-[var(--text-muted)]">Est. Duration</span>
                  </div>
                  <p className="text-lg font-bold font-mono" style={{ color: "var(--primary)" }}>{durationResult.estimated_duration_human}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">{durationResult.estimated_hours.toFixed(2)} hours</p>
                </div>
                <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-2">
                    <Gauge className="w-4 h-4" style={{ color: "var(--info)" }} />
                    <span className="text-xs text-[var(--text-muted)]">Theoretical</span>
                  </div>
                  <p className="text-lg font-bold font-mono" style={{ color: "var(--info)" }}>{durationResult.theoretical_hours.toFixed(2)}h</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">Physics formula (6ND)</p>
                </div>
                <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                  <div className="flex items-center gap-2 mb-2">
                    <Cpu className="w-4 h-4" style={{ color: "var(--text-secondary)" }} />
                    <span className="text-xs text-[var(--text-muted)]">GPU</span>
                  </div>
                  <p className="text-lg font-bold font-mono text-[var(--text)]">{durationResult.gpu_id}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">×{durationResult.n_gpus}</p>
                </div>
                {durationResult.estimated_cost_usd !== null ? (
                  <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4" style={{ color: "var(--success)" }} />
                      <span className="text-xs text-[var(--text-muted)]">Est. Cost</span>
                    </div>
                    <p className="text-lg font-bold font-mono" style={{ color: "var(--success)" }}>{formatUSD(durationResult.estimated_cost_usd)}</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">@ {formatUSD(durationResult.hourly_rate_usd || 0)}/h · {durationResult.cost_provider}</p>
                  </div>
                ) : (
                  <div className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                    <div className="flex items-center gap-2 mb-2">
                      <DollarSign className="w-4 h-4 text-[var(--text-muted)]" />
                      <span className="text-xs text-[var(--text-muted)]">Est. Cost</span>
                    </div>
                    <p className="text-lg font-bold font-mono text-[var(--text-muted)]">N/A</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1">Select a cloud provider</p>
                  </div>
                )}
              </div>

              {/* ML vs Theoretical comparison */}
              {durationResult.theoretical_hours > 0 && (
                <div className="mt-4">
                  <div className="text-xs text-[var(--text-muted)] mb-2">ML Prediction vs Physics Formula</div>
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
                  <div className="mt-2 text-xs text-[var(--text-muted)]">
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

        {/* Divider */}
        <div className="border-t border-[var(--border)] pt-6">
          <div className="flex items-center gap-2 mb-4">
            <FlaskConical className="w-4 h-4 text-[var(--text-muted)]" />
            <h3 className="text-sm font-medium text-[var(--text)]">Pre-Training Estimates</h3>
            <Badge variant="warning">PLACEHOLDER</Badge>
            <span className="text-xs text-[var(--text-muted)]">— These fields are not yet backed by backend endpoints</span>
          </div>
        </div>

        {/* Existing Analysis Form */}
        <Card title="Training Configuration">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Select label="Model Type" value={modelType} onChange={(v) => setModelType(v as ModelType)}
              options={[{value:"transformer",label:"Transformer"},{value:"vision",label:"Vision"},{value:"cnn",label:"CNN"}]} />
            <NumberInput label="Parameters (B)" value={params} onChange={setParams} step={0.1} min={0.01} />
            <Select label="Training Mode" value={mode} onChange={(v) => setMode(v as TrainingMode)}
              options={[{value:"full",label:"Full Fine-Tune"},{value:"lora",label:"LoRA"},{value:"inference",label:"Inference"}]} />
            <Select label="Precision" value={precision} onChange={(v) => setPrecision(v as Precision)}
              options={[{value:"fp32",label:"FP32"},{value:"fp16",label:"FP16"},{value:"int8",label:"INT8"}]} />
            <NumberInput label="Batch Size" value={batchSize} onChange={setBatchSize} min={1} />
            <NumberInput label="Learning Rate" value={lr} onChange={setLr} step={0.0001} min={0} />
            <Select label="Optimizer" value={optimizer} onChange={setOptimizer}
              options={[{value:"adam",label:"Adam"},{value:"adamw",label:"AdamW"},{value:"sgd",label:"SGD"},{value:"lion",label:"Lion"}]} />
            <Select label="Scheduler" value={scheduler} onChange={setScheduler}
              options={[{value:"cosine",label:"Cosine"},{value:"linear",label:"Linear"},{value:"step",label:"Step"},{value:"constant",label:"Constant"}]} />
            <NumberInput label="Epochs" value={epochs} onChange={setEpochs} min={1} />
            {modelType === "transformer" && <NumberInput label="Sequence Length" value={seqLen} onChange={setSeqLen} min={1} />}
            {modelType === "vision" && <NumberInput label="Image Size" value={imgSize} onChange={setImgSize} min={32} />}
            <NumberInput label="Dataset Size (samples)" value={datasetSize} onChange={setDatasetSize} step={1000} min={1} />
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={handleAnalyze} loading={loading}>
              <FlaskConical className="w-4 h-4" /> Analyze
            </Button>
          </div>
        </Card>

        {error && <Alert severity="error" title="Analysis Failed">{error}</Alert>}

        {/* Results */}
        {result && predictions && (
          <div className="space-y-6">
            {/* Predictions Grid */}
            <Card title="Predictions" action={<Badge variant="warning">Estimates</Badge>}>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {predictionCards.map((card) => {
                  const Icon = card.icon
                  return (
                    <div key={card.label} className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className="w-4 h-4" style={{ color: card.color }} />
                        <span className="text-xs text-[var(--text-muted)]">{card.label}</span>
                      </div>
                      <p className="text-lg font-bold font-mono" style={{ color: card.color }}>{card.value}</p>
                    </div>
                  )
                })}
              </div>
              {predictions.bottlenecks.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs text-[var(--text-muted)] mb-2">Expected Bottlenecks</div>
                  <div className="flex flex-wrap gap-2">
                    {predictions.bottlenecks.map((b, i) => (
                      <Badge key={i} variant="warning">{b}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            {/* AI Explanation */}
            <Card title="AI Explanation" action={<Badge variant="info">PLACEHOLDER</Badge>}>
              <div className="space-y-4">
                <p className="text-sm text-[var(--text-secondary)]">{result.explanation.summary}</p>

                <div className="space-y-2">
                  <div className="text-xs font-medium text-[var(--text)]">Reasoning</div>
                  {result.explanation.reasoning.map((r, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <span className="text-[var(--text-muted)] shrink-0">•</span>
                      <div>
                        <span className="text-[var(--text)] font-medium">{r.factor}: </span>
                        <span className="text-[var(--text-secondary)]">{r.impact}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <Alert severity="success" title="Estimated Savings">
                  {result.explanation.recommendations_savings}
                </Alert>

                <div className="space-y-2">
                  <div className="text-xs font-medium text-[var(--text)] flex items-center gap-2">
                    <CheckSquare className="w-4 h-4 text-[var(--success)]" /> Action Checklist
                  </div>
                  {result.explanation.action_checklist.map((item, i) => (
                    <div key={i} className="flex items-center gap-3 text-sm text-[var(--text-secondary)]">
                      <div className="w-4 h-4 rounded border border-[var(--border)]" />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            {/* Recommendations */}
            <Card title="Recommendations" action={<Badge variant="info">{result.recommendations.length} rules</Badge>}>
              <div className="space-y-3">
                {result.recommendations.map((rec) => (
                  <div key={rec.rule_id} className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Lightbulb className="w-4 h-4 text-[var(--warning)]" />
                        <span className="text-sm font-medium text-[var(--text)]">{rec.title}</span>
                      </div>
                      <div className="flex gap-2">
                        <Badge variant={rec.priority >= 8 ? "danger" : rec.priority >= 6 ? "warning" : "muted"}>
                          P{rec.priority}
                        </Badge>
                        <Badge variant="info">{confidencePercent(rec.confidence)}</Badge>
                      </div>
                    </div>
                    <p className="text-sm text-[var(--text-secondary)] mb-1">{rec.recommendation}</p>
                    <p className="text-xs text-[var(--text-muted)]">{rec.reason}</p>
                    {rec.source && (
                      <div className="text-xs text-[var(--text-muted)] mt-2">Source: {rec.source}</div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {!result && !loading && !error && !durationResult && (
          <Card>
            <EmptyState
              icon={<FlaskConical className="w-6 h-6 text-[var(--text-muted)]" />}
              title="No analysis yet"
              description="Run an ML duration prediction above, or configure your training parameters below and click Analyze to see estimates and recommendations."
            />
          </Card>
        )}
      </div>
    </>
  )
}
