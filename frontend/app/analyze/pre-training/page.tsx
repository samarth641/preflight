"use client"

import { useState } from "react"
import { TopBar } from "@/components/layout/TopBar"
import { Card } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Select } from "@/components/ui/Select"
import { NumberInput } from "@/components/ui/NumberInput"
import { Badge } from "@/components/ui/Badge"
import { Alert } from "@/components/ui/Alert"
import { FullSpinner } from "@/components/ui/Spinner"
import { EmptyState } from "@/components/ui/EmptyState"
import { DollarSign, Clock, MemoryStick, AlertTriangle, Target, Cpu, Leaf, Lightbulb, CheckSquare, FlaskConical, Rocket } from "lucide-react"
import { analyzeTraining } from "@/lib/api"
import { formatUSD, formatHours, formatGB, formatPercent, confidencePercent } from "@/lib/utils"
import { usePageResults } from "@/components/providers/PageResultsContext"
import type { AnalysisResult, AnalysisRequest, ModelType, TrainingMode, Precision } from "@/lib/types"

export default function PreTrainingPage() {
  const { preTraining, setPreTraining } = usePageResults()
  const cached = preTraining as { result: AnalysisResult | null; formState: Record<string, unknown> } | null

  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(cached?.result ?? null)
  const [error, setError] = useState<string | null>(null)

  const [modelType, setModelType] = useState<ModelType>((cached?.formState?.modelType as ModelType) ?? "transformer")
  const [params, setParams] = useState((cached?.formState?.params as number) ?? 7.1)
  const [mode, setMode] = useState<TrainingMode>((cached?.formState?.mode as TrainingMode) ?? "lora")
  const [precision, setPrecision] = useState<Precision>((cached?.formState?.precision as Precision) ?? "fp16")
  const [batchSize, setBatchSize] = useState((cached?.formState?.batchSize as number) ?? 4)
  const [lr, setLr] = useState((cached?.formState?.lr as number) ?? 0.001)
  const [optimizer, setOptimizer] = useState((cached?.formState?.optimizer as string) ?? "adamw")
  const [scheduler, setScheduler] = useState((cached?.formState?.scheduler as string) ?? "cosine")
  const [epochs, setEpochs] = useState((cached?.formState?.epochs as number) ?? 3)
  const [seqLen, setSeqLen] = useState((cached?.formState?.seqLen as number) ?? 576)
  const [imgSize, setImgSize] = useState((cached?.formState?.imgSize as number) ?? 224)
  const [datasetSize, setDatasetSize] = useState((cached?.formState?.datasetSize as number) ?? 2000000)

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
      setPreTraining({
        result: data,
        formState: { modelType, params, mode, precision, batchSize, lr, optimizer, scheduler, epochs, seqLen, imgSize, datasetSize },
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed")
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <FullSpinner label="Analyzing training configuration..." />

  const predictions = result?.predictions
  // OOM Risk color: warning (amber) for low, danger (red) for high
  // Previously green — changed per color psychology: risk should never read as "safe"
  const predictionCards = predictions ? [
    { label: "Est. Cost", value: formatUSD(predictions.estimated_cost_usd), icon: DollarSign, color: "var(--success)", primary: true },
    { label: "Est. Runtime", value: formatHours(predictions.estimated_runtime_hours), icon: Clock, color: "var(--primary)", primary: true },
    { label: "Peak VRAM", value: formatGB(predictions.peak_vram_gb), icon: MemoryStick, color: "var(--info)", primary: true },
    { label: "OOM Risk", value: formatPercent(predictions.oom_probability), icon: AlertTriangle, color: predictions.oom_probability > 0.5 ? "var(--danger)" : "var(--warning)", primary: false },
    { label: "Convergence", value: formatPercent(predictions.convergence_probability), icon: Target, color: predictions.convergence_probability > 0.7 ? "var(--success)" : "var(--warning)", primary: false },
    { label: "Accuracy Range", value: `${formatPercent(predictions.expected_accuracy_min, 0)}-${formatPercent(predictions.expected_accuracy_max, 0)}`, icon: Target, color: "var(--primary)", primary: false },
    { label: "GPU Utilization", value: formatPercent(predictions.gpu_utilization_estimate), icon: Cpu, color: "var(--info)", primary: false },
    { label: "Carbon", value: `${predictions.carbon_footprint_kg.toFixed(1)} kg CO₂e`, icon: Leaf, color: "var(--text-muted)", primary: false },
  ] : []

  return (
    <>
      <TopBar title="Pre-Training Estimates" subtitle="Predict outcomes before allocating GPU resources" />
      <div className="p-6 space-y-6">
        <div className="flex items-center gap-2">
          <Rocket className="w-4 h-4 text-[var(--text-muted)]" />
          <Badge variant="muted">Roadmap</Badge>
          <span className="text-xs text-[var(--text-muted)]">— Advanced prediction fields, not yet backed by backend endpoints</span>
        </div>

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
          <div className="mt-5 flex gap-3">
            <Button onClick={handleAnalyze} loading={loading}>
              <FlaskConical className="w-4 h-4" /> Analyze
            </Button>
          </div>
        </Card>

        {error && <Alert severity="error" title="Analysis Failed">{error}</Alert>}

        {result && predictions && (
          <div className="space-y-6">
            <Card title="Predictions" action={<Badge variant="warning">Estimates</Badge>}>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {predictionCards.map((card) => {
                  const Icon = card.icon
                  return (
                    <div key={card.label} className="p-5 rounded-lg border border-[var(--border)] bg-[var(--bg)]">
                      <div className="flex items-center gap-2 mb-3">
                        <Icon className="w-4 h-4" style={{ color: card.color }} />
                        <span className="text-xs text-[var(--text-muted)]">{card.label}</span>
                      </div>
                      <p className={`${card.primary ? "text-2xl font-bold" : "text-xl font-semibold"} font-mono leading-tight`} style={{ color: card.color }}>{card.value}</p>
                    </div>
                  )
                })}
              </div>
            </Card>

            {predictions.bottlenecks.length > 0 && (
              <Alert severity="warning" title="Expected Bottlenecks">
                <div className="flex flex-wrap gap-2 mt-2">
                  {predictions.bottlenecks.map((b, i) => (
                    <Badge key={i} variant="warning">{b}</Badge>
                  ))}
                </div>
              </Alert>
            )}

            {/* AI Explanation + Recommendations — side-by-side grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card title="AI Explanation" action={<Badge variant="muted">Roadmap</Badge>}>
                <div className="space-y-4">
                  <p className="text-sm text-[var(--text-secondary)] leading-relaxed">{result.explanation.summary}</p>
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
                      <p className="text-sm text-[var(--text-secondary)] mb-1 leading-relaxed">{rec.recommendation}</p>
                      <p className="text-xs text-[var(--text-muted)]">{rec.reason}</p>
                      {rec.source && (
                        <div className="text-xs text-[var(--text-muted)] mt-2">Source: {rec.source}</div>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>
        )}

        {!result && !loading && !error && (
          <Card>
            <EmptyState
              icon={<FlaskConical className="w-6 h-6 text-[var(--text-muted)]" />}
              title="No analysis yet"
              description="Configure your training parameters above and click Analyze to see estimates and recommendations."
            />
          </Card>
        )}
      </div>
    </>
  )
}
