// API client — calls Preflight backend with mock fallback for frontend-only features

import type {
  GPUSpec, CloudOffering, GPURecommendationRequest, GPURecommendationResult,
  DatasetAnalysisResult, DatasetManualInput, AnalysisRequest, AnalysisResult,
  ActivityItem, HealthStatus, Settings,
  EpochMetrics, TrainingAnalysisResult,
  DurationPredictRequest, DurationPredictResult,
  CostEstimateRequest, CostEstimateResult, GPUBenchmark,
  ExperimentHistoryResponse, DashboardStats,
  LiveTrainingMonitor, EpochPoint,
} from "./types"

import {
  MOCK_GPUS, MOCK_CLOUD, MOCK_GPU_RESULT, MOCK_DATASET_RESULT,
  MOCK_ANALYSIS_RESULT, MOCK_DASHBOARD_STATS, MOCK_ACTIVITY,
  MOCK_HEALTH, DEFAULT_SETTINGS,
  MOCK_EPOCH_DATA, MOCK_TRAINING_RESULT,
  GPU_BENCHMARKS, MOCK_DURATION_PREDICTION, MOCK_COST_ESTIMATE,
  MOCK_EXPERIMENT_HISTORY, MOCK_LIVE_MONITOR,
} from "./mock-data"

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1"
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true"
const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"

/** Map demo training job ids to backend experiment ids */
const DEMO_JOB_TO_EXPERIMENT: Record<string, string> = {
  "demo-vit-base-live": "exp-live-100m",
}

class ApiError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "ApiError"
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({})) as { detail?: string | unknown }
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? res.statusText)
    throw new ApiError(detail || `Request failed (${res.status})`)
  }
  return body as T
}

async function withBackend<T>(path: string, init: RequestInit | undefined, mockFn: () => Promise<T>): Promise<T> {
  if (USE_MOCK) return mockFn()
  try {
    return await apiFetch<T>(path, init)
  } catch (err) {
    // Fall back to mocks in local dev or hackathon demo mode when backend is unreachable
    if (process.env.NODE_ENV === "development" || DEMO_MODE) {
      console.warn(`[api] ${path} failed, using mock:`, err)
      return mockFn()
    }
    throw err
  }
}

function enrichCostResult(data: CostEstimateResult, gpuCount: number): CostEstimateResult {
  return {
    ...data,
    gpu_hours: data.gpu_hours ?? parseFloat((data.estimated_hours * gpuCount).toFixed(2)),
  }
}

function liveMonitorToTrainingResult(live: LiveTrainingMonitor): TrainingAnalysisResult {
  return {
    log_path: null,
    metrics: {
      epoch_count: live.total_epochs,
      current_epoch: live.epoch,
      latest_train_loss: live.train_loss,
      latest_val_loss: live.val_loss,
      best_val_loss: live.val_loss,
      best_epoch: live.epoch,
      validation_loss_increasing: live.convergence_status === "diverging",
      train_loss_stagnant: live.convergence_status === "stagnant",
      overfitting_gap: 0,
      overfitting_detected: live.convergence_status === "plateau",
      loss_diverging: live.convergence_status === "diverging",
      accuracy_plateau: live.convergence_status === "plateau",
      gpu_utilization: live.gpu_utilization,
      cpu_utilization: null,
      avg_gpu_utilization: live.gpu_utilization,
      vram_usage_percent: null,
      vram_near_limit: false,
    },
    trends: [],
    score: live.health_score,
    grade: live.health_grade,
    warnings: live.warnings,
    recommendations: live.recommendations,
    sources: [],
  }
}

function curveToEpochMetrics(curve: EpochPoint[]): EpochMetrics[] {
  return curve.map((p) => ({
    epoch: p.epoch,
    train_loss: p.train_loss,
    val_loss: p.val_loss,
    accuracy: p.accuracy,
    gpu_utilization: p.gpu_utilization,
    cpu_utilization: null,
    vram_gb: null,
    vram_percent: null,
    power_watts: null,
  }))
}

function experimentsToActivity(history: ExperimentHistoryResponse): ActivityItem[] {
  return history.experiments.map((exp) => ({
    id: exp.id,
    type: exp.status === "running" ? "training" as const : "analysis" as const,
    title: exp.name,
    description: `${exp.params_million}M params · ${exp.gpu} · ${exp.status}${exp.final_accuracy != null ? ` · ${(exp.final_accuracy * 100).toFixed(1)}% acc` : ""}`,
    timestamp: exp.started_at || new Date().toISOString(),
  }))
}

// ─── Health & System ───

export async function getHealth(): Promise<HealthStatus> {
  return withBackend("/health", { method: "GET" }, async () => ({ ...MOCK_HEALTH }))
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return withBackend("/dashboard/stats", { method: "GET" }, async () => ({ ...MOCK_DASHBOARD_STATS }))
}

export async function getRecentActivity(): Promise<ActivityItem[]> {
  if (USE_MOCK) return [...MOCK_ACTIVITY]
  try {
    const history = await apiFetch<ExperimentHistoryResponse>("/experiments", { method: "GET" })
    return experimentsToActivity(history)
  } catch {
    return [...MOCK_ACTIVITY]
  }
}

// ─── Pre-training analysis (composed from real GPU + cost + duration APIs) ───

export async function analyzeTraining(req: AnalysisRequest): Promise<AnalysisResult> {
  if (USE_MOCK) {
    const result = JSON.parse(JSON.stringify(MOCK_ANALYSIS_RESULT)) as AnalysisResult
    const vramMultiplier = req.parameter_count_billion / 7.0
    result.predictions.peak_vram_gb = parseFloat((18.5 * vramMultiplier).toFixed(1))
    result.predictions.estimated_cost_usd = parseFloat((12.5 * vramMultiplier).toFixed(2))
    result.predictions.estimated_runtime_hours = parseFloat((4.5 * vramMultiplier).toFixed(1))
    return result
  }

  const gpuId = req.gpu_id ?? "rtx-4090"
  const [gpu, duration, cost] = await Promise.all([
    recommendGPU({
      parameter_count_billion: req.parameter_count_billion,
      batch_size: req.batch_size,
      precision: req.precision,
      training_mode: req.training_mode,
      model_type: req.model_type,
      image_size: req.image_size ?? 224,
      sequence_length: req.sequence_length ?? 512,
      budget_tier: null,
      preferred_vendor: null,
      max_results: 3,
      include_cloud: true,
      include_cost: true,
      epochs: req.epochs,
      dataset_samples: req.dataset_size,
      dataset_size_gb: null,
      deployment: "cloud",
    }),
    predictDuration({
      parameter_count_billion: req.parameter_count_billion,
      dataset_tokens: req.dataset_size,
      gpu_id: gpuId,
      n_gpus: 1,
      epochs: req.epochs,
      domain: req.model_type === "transformer" ? "language" : "vision",
      cloud_provider: "runpod",
    }),
    estimateCost({
      parameter_count_billion: req.parameter_count_billion,
      gpu_id: gpuId,
      epochs: req.epochs,
      dataset_samples: req.dataset_size,
      dataset_size_gb: null,
      batch_size: req.batch_size,
      model_type: req.model_type,
      deployment: "cloud",
      cloud_provider: "runpod",
      electricity_usd_per_kwh: null,
      gpu_count: 1,
    }),
  ])

  const peakVram = gpu.required_vram_gb
  const headroomRisk = gpu.best_pick?.vram_utilization ?? 0.5

  return {
    predictions: {
      estimated_cost_usd: cost.total_usd,
      estimated_runtime_hours: duration.estimated_hours,
      peak_vram_gb: peakVram,
      oom_probability: parseFloat(Math.min(0.95, Math.max(0.02, headroomRisk - 0.5)).toFixed(2)),
      convergence_probability: parseFloat(Math.min(0.95, 0.55 + (duration.estimated_hours < 24 ? 0.2 : 0)).toFixed(2)),
      expected_accuracy_min: 0.65,
      expected_accuracy_max: 0.92,
      gpu_utilization_estimate: 0.85,
      carbon_footprint_kg: parseFloat((duration.estimated_hours * 0.4).toFixed(2)),
      bottlenecks: headroomRisk > 0.9 ? ["VRAM near limit — reduce batch size or use LoRA"] : [],
    },
    recommendations: gpu.knowledge_recommendations,
    warnings: gpu.warnings,
    explanation: {
      summary: `Estimated ${duration.estimated_duration_human} on ${gpuId} for ${req.parameter_count_billion}B params (${req.training_mode}).`,
      reasoning: [
        { factor: "GPU fit", impact: gpu.best_pick ? `${gpu.best_pick.gpu.name} — ${gpu.best_pick.fit_rating}` : "See recommendations" },
        { factor: "Duration (ML)", impact: `${duration.estimated_hours.toFixed(1)}h (${duration.model_version})` },
        { factor: "Cost", impact: `$${cost.total_usd.toFixed(2)} on runpod` },
      ],
      recommendations_savings: "Use LoRA and a smaller cloud GPU for prototyping.",
      action_checklist: ["Run dataset quality check", "Confirm GPU recommendation", "Monitor training with live dashboard"],
    },
    sources: gpu.sources,
  }
}

// ─── Dataset ───

export async function analyzeDataset(input: DatasetManualInput | { path: string }): Promise<DatasetAnalysisResult> {
  if ("path" in input && !USE_MOCK) {
    return apiFetch("/dataset/analyze", {
      method: "POST",
      body: JSON.stringify({ path: input.path }),
    })
  }

  // Manual metrics mode — client-side scoring (no backend endpoint)
  const result = JSON.parse(JSON.stringify(MOCK_DATASET_RESULT)) as DatasetAnalysisResult
  if (!("path" in input)) {
    result.metrics.image_count = input.image_count
    result.metrics.class_count = input.class_count
    result.metrics.class_imbalance_ratio = input.class_imbalance_ratio
    result.metrics.duplicate_percent = input.duplicate_percent
    result.metrics.blur_percent = input.blur_percent
    result.metrics.missing_label_percent = input.missing_label_percent
    result.metrics.median_resolution = input.median_resolution
    let score = 100
    if (input.class_imbalance_ratio >= 5) score -= 15
    else if (input.class_imbalance_ratio >= 3) score -= 8
    if (input.duplicate_percent >= 5) score -= 12
    else if (input.duplicate_percent >= 3) score -= 6
    if (input.blur_percent >= 10) score -= 10
    else if (input.blur_percent >= 5) score -= 5
    if (input.missing_label_percent >= 5) score -= 15
    else if (input.missing_label_percent >= 2) score -= 5
    if (input.median_resolution < 224) score -= 8
    if (input.image_count < 500) score -= 10
    result.score = Math.max(0, score)
    result.grade = score >= 90 ? "A" : score >= 80 ? "B" : score >= 70 ? "C" : score >= 60 ? "D" : "F"
  }
  return result
}

// ─── GPU ───

export async function recommendGPU(req: GPURecommendationRequest): Promise<GPURecommendationResult> {
  return withBackend("/gpu/recommend", { method: "POST", body: JSON.stringify(req) }, async () => {
    const result = JSON.parse(JSON.stringify(MOCK_GPU_RESULT)) as GPURecommendationResult
    result.request = req
    return result
  })
}

export async function listGPUs(): Promise<GPUSpec[]> {
  if (!USE_MOCK) {
    try {
      const rec = await recommendGPU({
        parameter_count_billion: 7,
        batch_size: 8,
        precision: "fp16",
        training_mode: "lora",
        model_type: "transformer",
        image_size: 224,
        sequence_length: 512,
        budget_tier: null,
        preferred_vendor: null,
        max_results: 20,
        include_cloud: true,
        include_cost: false,
        epochs: 5,
        dataset_samples: 10_000,
        dataset_size_gb: null,
        deployment: "cloud",
      })
      const seen = new Set<string>()
      return rec.candidates.map((c) => c.gpu).filter((g) => {
        if (seen.has(g.id)) return false
        seen.add(g.id)
        return true
      })
    } catch { /* fall through */ }
  }
  return [...MOCK_GPUS]
}

export async function listCloudOfferings(): Promise<CloudOffering[]> {
  if (!USE_MOCK) {
    try {
      const rec = await recommendGPU({
        parameter_count_billion: 7,
        batch_size: 8,
        precision: "fp16",
        training_mode: "lora",
        model_type: "transformer",
        image_size: 224,
        sequence_length: 512,
        budget_tier: null,
        preferred_vendor: null,
        max_results: 5,
        include_cloud: true,
        include_cost: false,
        epochs: 5,
        dataset_samples: 10_000,
        dataset_size_gb: null,
        deployment: "cloud",
      })
      return rec.cloud_offerings
    } catch { /* fall through */ }
  }
  return [...MOCK_CLOUD]
}

// ─── Training Log Analysis ───

export async function getTrainingHealth(jobId: string): Promise<TrainingAnalysisResult> {
  const experimentId = DEMO_JOB_TO_EXPERIMENT[jobId]
  if (experimentId && !USE_MOCK) {
    try {
      const q = `?experiment_id=${encodeURIComponent(experimentId)}`
      const live = await apiFetch<LiveTrainingMonitor>(`/training/monitor${q}`, { method: "GET" })
      return liveMonitorToTrainingResult(live)
    } catch { /* fall through */ }
  }
  return JSON.parse(JSON.stringify(MOCK_TRAINING_RESULT))
}

// ─── Duration Prediction (ML) ───

export async function predictDuration(req: DurationPredictRequest): Promise<DurationPredictResult> {
  return withBackend("/predict/duration", { method: "POST", body: JSON.stringify(req) }, async () => {
    const result = JSON.parse(JSON.stringify(MOCK_DURATION_PREDICTION)) as DurationPredictResult
    result.gpu_id = req.gpu_id
    result.n_gpus = req.n_gpus
    return result
  })
}

// ─── Cost Estimation ───

export async function estimateCost(req: CostEstimateRequest): Promise<CostEstimateResult> {
  const data = await withBackend<CostEstimateResult>("/cost/estimate", {
    method: "POST",
    body: JSON.stringify(req),
  }, async () => JSON.parse(JSON.stringify(MOCK_COST_ESTIMATE)))
  return enrichCostResult(data, req.gpu_count)
}

// ─── GPU Benchmarks (from mock knowledge base — no dedicated API) ───

export async function listGPUBenchmarks(): Promise<Record<string, GPUBenchmark>> {
  return { ...GPU_BENCHMARKS }
}

// ─── Experiment History ───

export async function listExperiments(): Promise<ExperimentHistoryResponse> {
  return withBackend("/experiments", { method: "GET" }, async () =>
    JSON.parse(JSON.stringify(MOCK_EXPERIMENT_HISTORY)))
}

// ─── Live Training Monitor ───

export async function getLiveMonitor(experimentId?: string): Promise<LiveTrainingMonitor> {
  const q = experimentId ? `?experiment_id=${encodeURIComponent(experimentId)}` : ""
  return withBackend(`/training/monitor${q}`, { method: "GET" }, async () => {
    const result = JSON.parse(JSON.stringify(MOCK_LIVE_MONITOR)) as LiveTrainingMonitor
    if (experimentId) result.experiment_id = experimentId
    return result
  })
}

// ─── Training Controls (demo — uses live monitor data when available) ───

export async function startTraining(_req: { model: string; dataset: string; gpu: string }): Promise<{ job_id: string }> {
  return { job_id: "demo-vit-base-live" }
}

export async function getTrainingMetrics(jobId: string): Promise<EpochMetrics[]> {
  const experimentId = DEMO_JOB_TO_EXPERIMENT[jobId]
  if (experimentId && !USE_MOCK) {
    try {
      const live = await getLiveMonitor(experimentId)
      return curveToEpochMetrics(live.curve)
    } catch { /* fall through */ }
  }
  return [...MOCK_EPOCH_DATA]
}

export async function stopTraining(_jobId: string): Promise<{ status: string }> {
  return { status: "stopped" }
}

// ─── Settings (localStorage) ───

export async function getSettings(): Promise<Settings> {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("preflight-settings")
    if (saved) {
      try { return JSON.parse(saved) } catch { /* ignore */ }
    }
  }
  return { ...DEFAULT_SETTINGS }
}

export async function updateSettings(settings: Settings): Promise<Settings> {
  if (typeof window !== "undefined") {
    localStorage.setItem("preflight-settings", JSON.stringify(settings))
  }
  return { ...settings }
}

// ─── Export (frontend-only placeholder) ───

export async function exportAnalysis(_id: string, format: "pdf" | "json"): Promise<Blob> {
  const data = JSON.stringify(MOCK_ANALYSIS_RESULT, null, 2)
  return new Blob([data], { type: format === "json" ? "application/json" : "application/pdf" })
}
