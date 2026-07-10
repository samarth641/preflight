// API client — all functions return mock data
// When backend is ready, replace mock implementations with real fetch() calls
// Function signatures and return types stay identical

import type {
  GPUSpec, CloudOffering, GPURecommendationRequest, GPURecommendationResult,
  DatasetAnalysisResult, DatasetManualInput, AnalysisRequest, AnalysisResult,
  ActivityItem, HealthStatus, Settings,
  EpochMetrics, TrainingAnalysisResult,
  DurationPredictRequest, DurationPredictResult,
  CostEstimateRequest, CostEstimateResult, GPUBenchmark,
  ExperimentHistoryResponse, DashboardStats,
  LiveTrainingMonitor,
} from "./types"

import {
  MOCK_GPUS, MOCK_CLOUD, MOCK_GPU_RESULT, MOCK_DATASET_RESULT,
  MOCK_ANALYSIS_RESULT, MOCK_DASHBOARD_STATS, MOCK_ACTIVITY,
  MOCK_HEALTH, DEFAULT_SETTINGS,
  MOCK_EPOCH_DATA, MOCK_TRAINING_RESULT,
  GPU_BENCHMARKS, MOCK_DURATION_PREDICTION, MOCK_COST_ESTIMATE,
  MOCK_EXPERIMENT_HISTORY, MOCK_LIVE_MONITOR,
} from "./mock-data"

// Simulated network delay
function delay(ms: number = 800): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function randomDelay(): Promise<void> {
  return delay(500 + Math.random() * 1000)
}

// ─── Health & System ───

export async function getHealth(): Promise<HealthStatus> {
  await delay(300)
  return { ...MOCK_HEALTH }
}

export async function getDashboardStats(): Promise<DashboardStats> {
  await randomDelay()
  return { ...MOCK_DASHBOARD_STATS }
}

export async function getRecentActivity(): Promise<ActivityItem[]> {
  await randomDelay()
  return [...MOCK_ACTIVITY]
}

// ─── Analysis (PLACEHOLDER — no backend /analyze endpoint) ───

export async function analyzeTraining(req: AnalysisRequest): Promise<AnalysisResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_ANALYSIS_RESULT)) as AnalysisResult
  const vramMultiplier = req.parameter_count_billion / 7.0
  result.predictions.peak_vram_gb = parseFloat((18.5 * vramMultiplier).toFixed(1))
  result.predictions.estimated_cost_usd = parseFloat((12.5 * vramMultiplier).toFixed(2))
  result.predictions.estimated_runtime_hours = parseFloat((4.5 * vramMultiplier).toFixed(1))
  return result
}

// ─── Dataset ───

export async function analyzeDataset(input: DatasetManualInput | { path: string }): Promise<DatasetAnalysisResult> {
  await randomDelay()
  if ("path" in input) {
    return JSON.parse(JSON.stringify(MOCK_DATASET_RESULT))
  }
  const result = JSON.parse(JSON.stringify(MOCK_DATASET_RESULT)) as DatasetAnalysisResult
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
  return result
}

// ─── GPU ───

export async function recommendGPU(req: GPURecommendationRequest): Promise<GPURecommendationResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_GPU_RESULT)) as GPURecommendationResult
  const vramMultiplier = req.parameter_count_billion / 7.0
  result.required_vram_gb = parseFloat((18.5 * vramMultiplier).toFixed(1))
  result.request = req
  if (req.preferred_vendor) {
    result.candidates = result.candidates.filter(c => c.gpu.vendor === req.preferred_vendor)
    result.best_pick = result.candidates[0] || null
  }
  result.candidates = result.candidates.map(c => {
    const benchmark = GPU_BENCHMARKS[c.gpu.id]
    if (benchmark) {
      const existingReasons = c.reasons.filter(r => !r.includes("benchmark"))
      const benchmarkReason = `Benchmark: ${benchmark.relative_training_throughput}x A100 throughput`
      return { ...c, reasons: [...existingReasons, benchmarkReason] }
    }
    return c
  })
  if (result.best_pick) {
    const benchmark = GPU_BENCHMARKS[result.best_pick.gpu.id]
    if (benchmark) {
      const existingReasons = result.best_pick.reasons.filter(r => !r.includes("benchmark"))
      result.best_pick = { ...result.best_pick, reasons: [...existingReasons, `Benchmark: ${benchmark.relative_training_throughput}x A100 throughput`] }
    }
  }
  const candidateIds = new Set(result.candidates.slice(0, 3).map(c => c.gpu.id))
  result.cloud_offerings = MOCK_CLOUD.filter(c => candidateIds.has(c.gpu_id)).slice(0, 5)
  return result
}

export async function listGPUs(): Promise<GPUSpec[]> {
  await delay(300)
  return [...MOCK_GPUS]
}

export async function listCloudOfferings(): Promise<CloudOffering[]> {
  await delay(300)
  return [...MOCK_CLOUD]
}

// ─── Training Log Analysis ───

export async function getTrainingHealth(jobId: string): Promise<TrainingAnalysisResult> {
  await randomDelay()
  return JSON.parse(JSON.stringify(MOCK_TRAINING_RESULT))
}

// ─── Duration Prediction (ML) ───

export async function predictDuration(req: DurationPredictRequest): Promise<DurationPredictResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_DURATION_PREDICTION)) as DurationPredictResult
  const paramFactor = Math.pow(req.parameter_count_billion / 7.0, 0.75)
  const tokenFactor = req.dataset_tokens / 2_000_000
  const gpuBenchmark = GPU_BENCHMARKS[req.gpu_id]
  const throughputFactor = gpuBenchmark ? 1.0 / gpuBenchmark.relative_training_throughput : 1.0
  const multiGpuFactor = Math.pow(req.n_gpus, 0.95)
  const baseHours = 3.2 * paramFactor * tokenFactor * throughputFactor / multiGpuFactor * req.epochs
  result.estimated_hours = parseFloat(baseHours.toFixed(2))
  result.theoretical_hours = parseFloat((baseHours * 1.28).toFixed(2))
  result.gpu_id = req.gpu_id
  result.n_gpus = req.n_gpus
  const h = result.estimated_hours
  result.estimated_duration_human = h < 1 ? `${Math.round(h * 60)}m` : h < 48 ? `${h.toFixed(1)}h` : `${(h / 24).toFixed(1)} days`
  if (req.cloud_provider) {
    const rates: Record<string, number> = {
      "mi300x-azure": 6.00, "a100-80gb-aws": 32.77, "a100-80gb-gcp": 30.00,
      "a100-80gb-lambda": 1.10, "a100-80gb-runpod": 1.89,
      "h100-80gb-aws": 98.32, "h100-80gb-gcp": 90.00,
      "rtx-4090-runpod": 0.44, "rtx-4090-lambda": 0.50, "rtx-4090-vast": 0.35,
      "rtx-4080-runpod": 0.34,
    }
    const rateKey = `${req.gpu_id}-${req.cloud_provider}`
    const rate = rates[rateKey]
    if (rate) {
      result.estimated_cost_usd = parseFloat((baseHours * req.n_gpus * rate).toFixed(2))
      result.cost_provider = req.cloud_provider
      result.hourly_rate_usd = rate
    } else {
      result.estimated_cost_usd = null
      result.cost_provider = null
      result.hourly_rate_usd = null
    }
  } else {
    result.estimated_cost_usd = null
    result.cost_provider = null
    result.hourly_rate_usd = null
  }
  return result
}

// ─── Cost Estimation ───

export async function estimateCost(req: CostEstimateRequest): Promise<CostEstimateResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_COST_ESTIMATE)) as CostEstimateResult
  const paramFactor = Math.pow(req.parameter_count_billion / 7.0, 0.75)
  const datasetFactor = req.dataset_samples / 10_000
  const gpuBenchmark = GPU_BENCHMARKS[req.gpu_id]
  const throughputFactor = gpuBenchmark ? 1.0 / gpuBenchmark.relative_training_throughput : 1.0
  const multiGpuFactor = Math.pow(req.gpu_count, 0.95)
  const singleGpuSeconds = 3600 * paramFactor * datasetFactor * throughputFactor
  const parallelism = multiGpuFactor
  const wallClockSeconds = singleGpuSeconds / parallelism
  const wallClockHours = (wallClockSeconds * req.epochs) / 3600
  const gpuHours = wallClockHours * req.gpu_count
  result.gpu_id = req.gpu_id
  result.estimated_hours = parseFloat(wallClockHours.toFixed(2))
  result.estimated_days = parseFloat((wallClockHours / 24).toFixed(2))
  result.gpu_hours = parseFloat(gpuHours.toFixed(2))
  result.seconds_per_epoch = parseFloat(wallClockSeconds.toFixed(1))
  result.deployment = req.deployment
  result.cloud_provider = req.cloud_provider ?? null
  if (req.deployment === "cloud" && req.cloud_provider) {
    const rates: Record<string, number> = {
      "mi300x-azure": 6.00, "a100-80gb-aws": 32.77, "a100-80gb-gcp": 30.00,
      "a100-80gb-azure": 3.67, "a100-80gb-lambda": 1.10, "a100-80gb-runpod": 1.89,
      "h100-80gb-aws": 98.32, "h100-80gb-gcp": 90.00, "h100-80gb-azure": 6.98,
      "rtx-4090-runpod": 0.44, "rtx-4090-lambda": 0.50, "rtx-4090-vast": 0.35,
      "rtx-4080-runpod": 0.34,
    }
    const rate = rates[`${req.gpu_id}-${req.cloud_provider}`]
    if (rate) {
      result.hourly_rate_usd = rate
      result.breakdown.cloud_usd = parseFloat((gpuHours * rate).toFixed(2))
      result.total_usd = parseFloat((result.breakdown.cloud_usd + result.breakdown.storage_usd + result.breakdown.bandwidth_usd).toFixed(2))
      result.notes = gpuBenchmark && !gpuBenchmark.approximate
        ? ["Training speed from benchmark (MLPerf A100 baseline)."]
        : gpuBenchmark
          ? [`Training speed from benchmark (${gpuBenchmark.source}).`]
          : ["Training speed estimated from peak TFLOPS (no benchmark data)."]
      if (req.gpu_count > 1) {
        result.notes.push(`${req.gpu_count} GPUs at ~0.95 scaling — wall-clock ${wallClockHours.toFixed(1)}h, billed as ${gpuHours.toFixed(1)} GPU-hours.`)
      }
    } else {
      result.hourly_rate_usd = null
      result.breakdown.cloud_usd = 0
      result.total_usd = parseFloat((result.breakdown.storage_usd + result.breakdown.bandwidth_usd).toFixed(2))
      result.notes = ["No cloud pricing for this GPU — using electricity estimate only."]
    }
  } else {
    result.hourly_rate_usd = null
    result.breakdown.cloud_usd = 0
    const powerWatts = GPU_BENCHMARKS[req.gpu_id] ? 750 : 400
    result.breakdown.electricity_usd = parseFloat(((powerWatts / 1000) * gpuHours * 0.12).toFixed(2))
    result.total_usd = parseFloat((result.breakdown.electricity_usd + result.breakdown.storage_usd + result.breakdown.bandwidth_usd).toFixed(2))
    result.notes = ["Local deployment — cloud cost is zero."]
  }
  return result
}

// ─── GPU Benchmarks ───

export async function listGPUBenchmarks(): Promise<Record<string, GPUBenchmark>> {
  await delay(200)
  return { ...GPU_BENCHMARKS }
}

// ─── Experiment History (matches GET /api/v1/experiments) ───

export async function listExperiments(): Promise<ExperimentHistoryResponse> {
  await randomDelay()
  return JSON.parse(JSON.stringify(MOCK_EXPERIMENT_HISTORY))
}

// ─── Live Training Monitor (matches GET /api/v1/training/monitor) ───

export async function getLiveMonitor(experimentId?: string): Promise<LiveTrainingMonitor> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_LIVE_MONITOR)) as LiveTrainingMonitor
  if (experimentId) {
    result.experiment_id = experimentId
  }
  return result
}

// ─── Training Controls (frontend-only — no backend) ───

export async function startTraining(req: { model: string; dataset: string; gpu: string }): Promise<{ job_id: string }> {
  await randomDelay()
  return { job_id: `job-${Date.now()}` }
}

export async function getTrainingMetrics(jobId: string): Promise<EpochMetrics[]> {
  await randomDelay()
  return [...MOCK_EPOCH_DATA]
}

export async function stopTraining(jobId: string): Promise<{ status: string }> {
  await delay(500)
  return { status: "stopped" }
}

// ─── Settings ───

export async function getSettings(): Promise<Settings> {
  await delay(200)
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("preflight-settings")
    if (saved) {
      try { return JSON.parse(saved) } catch { /* ignore */ }
    }
  }
  return { ...DEFAULT_SETTINGS }
}

export async function updateSettings(settings: Settings): Promise<Settings> {
  await delay(300)
  if (typeof window !== "undefined") {
    localStorage.setItem("preflight-settings", JSON.stringify(settings))
  }
  return { ...settings }
}

// ─── Export (PLACEHOLDER) ───

export async function exportAnalysis(id: string, format: "pdf" | "json"): Promise<Blob> {
  await delay(1000)
  const data = JSON.stringify(MOCK_ANALYSIS_RESULT, null, 2)
  return new Blob([data], { type: format === "json" ? "application/json" : "application/pdf" })
}
