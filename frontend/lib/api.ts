// ─────────────────────────────────────────────────────────────────
// API Client
//
// Right now everything here returns mock data. See INTEGRATION.md
// for how to swap each function to a real fetch() call.
//
// The key thing: function signatures and return types are the contract.
// Components only import from here — they never call fetch directly.
// When you switch to real API calls, only this file changes.
// ─────────────────────────────────────────────────────────────────

import type {
  GPUSpec, CloudOffering, GPURecommendationRequest, GPURecommendationResult,
  DatasetAnalysisResult, DatasetManualInput, AnalysisRequest, AnalysisResult,
  DashboardStats, ActivityItem, HealthStatus, Experiment, ExperimentDetail,
  EpochMetrics, TrainingAnalysisResult, Settings,
} from "./types"

import {
  MOCK_GPUS, MOCK_CLOUD, MOCK_GPU_RESULT, MOCK_DATASET_RESULT,
  MOCK_ANALYSIS_RESULT, MOCK_DASHBOARD_STATS, MOCK_ACTIVITY,
  MOCK_HEALTH, MOCK_EXPERIMENTS, MOCK_EXPERIMENT_DETAIL,
  MOCK_EPOCH_DATA, MOCK_TRAINING_RESULT, DEFAULT_SETTINGS,
  MOCK_RECS,
} from "./mock-data"

// When connecting for real, read this from env:
// const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

// Fake network delay so the UI feels realistic in mock mode.
// Delete these two functions when switching to real API calls.
function delay(ms: number = 800): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function randomDelay(): Promise<void> {
  return delay(500 + Math.random() * 1000)
}

// ─── Health & System ───

// Backend: GET /api/v1/health — ready to connect
export async function getHealth(): Promise<HealthStatus> {
  await delay(300)
  return { ...MOCK_HEALTH }
}

// Backend: no endpoint yet — needs GET /api/v1/dashboard/stats
export async function getDashboardStats(): Promise<DashboardStats> {
  await randomDelay()
  return { ...MOCK_DASHBOARD_STATS }
}

// Backend: no endpoint yet — part of dashboard stats
export async function getRecentActivity(): Promise<ActivityItem[]> {
  await randomDelay()
  return [...MOCK_ACTIVITY]
}

// ─── Analysis (Pre-Training Predictions) ───

// Backend: no endpoint yet — needs POST /api/v1/predict
// This is the big one — cost, runtime, VRAM, OOM, convergence, accuracy predictions.
// The mock adjusts VRAM/cost/runtime based on model size to feel somewhat realistic.
export async function analyzeTraining(req: AnalysisRequest): Promise<AnalysisResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_ANALYSIS_RESULT)) as AnalysisResult
  const vramMultiplier = req.parameter_count_billion / 7.0
  result.predictions.peak_vram_gb = parseFloat((18.5 * vramMultiplier).toFixed(1))
  result.predictions.estimated_cost_usd = parseFloat((12.5 * vramMultiplier).toFixed(2))
  result.predictions.estimated_runtime_hours = parseFloat((4.5 * vramMultiplier).toFixed(1))
  return result
}

export async function getRecommendations(): Promise<typeof MOCK_RECS> {
  await delay(300)
  return [...MOCK_RECS]
}

// ─── Dataset ───

// Backend: POST /api/v1/dataset/analyze — ready to connect
//
// Note: the backend takes a server-side file path ({ path, max_images }).
// The "path" mode here maps directly to that.
// The "manual entry" mode (DatasetManualInput) lets users enter metrics
// without uploading anything — the backend doesn't support this yet.
// You could either add a POST /api/v1/dataset/analyze-metrics endpoint,
// or accept metrics in the existing endpoint's body.
export async function analyzeDataset(input: DatasetManualInput | { path: string }): Promise<DatasetAnalysisResult> {
  await randomDelay()
  if ("path" in input) {
    // Real call would be:
    // const res = await fetch(`${API_URL}/dataset/analyze`, {
    //   method: "POST", headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify(input),
    // })
    // return res.json()
    return JSON.parse(JSON.stringify(MOCK_DATASET_RESULT))
  }
  // Manual mode — compute a rough score from the entered metrics.
  // This is just for demo purposes; the real scoring logic is in the backend.
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

// Backend: POST /api/v1/gpu/recommend — ready to connect
//
// Your backend now includes cost_estimate per candidate and cheapest_gpu.
// The frontend types in types.ts need updating to include these fields
// when you connect for real. See INTEGRATION.md section 7.
//
// Request fields the backend now accepts that we don't send yet:
//   include_cost, epochs, dataset_samples, dataset_size_gb, deployment
// Add these to GPURecommendationRequest in types.ts and to the form
// when you're ready to wire them up.
export async function recommendGPU(req: GPURecommendationRequest): Promise<GPURecommendationResult> {
  await randomDelay()
  const result = JSON.parse(JSON.stringify(MOCK_GPU_RESULT)) as GPURecommendationResult
  const vramMultiplier = req.parameter_count_billion / 7.0
  result.required_vram_gb = parseFloat((18.5 * vramMultiplier).toFixed(1))
  if (req.preferred_vendor) {
    result.candidates = result.candidates.filter(c => c.gpu.vendor === req.preferred_vendor)
    result.best_pick = result.candidates[0] || null
  }
  const candidateIds = new Set(result.candidates.slice(0, 3).map(c => c.gpu.id))
  result.cloud_offerings = MOCK_CLOUD.filter(c => candidateIds.has(c.gpu_id)).slice(0, 5)
  return result
}

// Backend: GET /api/v1/gpus — can be derived from knowledge/hardware/gpus.yaml
// or add a simple endpoint that returns the GPU list.
export async function listGPUs(): Promise<GPUSpec[]> {
  await delay(300)
  return [...MOCK_GPUS]
}

// Backend: GET /api/v1/cloud — same, from knowledge/hardware/cloud.yaml
export async function listCloudOfferings(): Promise<CloudOffering[]> {
  await delay(300)
  return [...MOCK_CLOUD]
}

// ─── Training ───

// Backend: POST /api/v1/training/analyze — ready to connect
// But note: the backend analyzes a log FILE (server-side path), not a live job.
// The "connect job ID" UI here is for future live monitoring via WebSocket.
//
// For now, you can wire startTraining to return a fake job ID, then
// getTrainingMetrics/getTrainingHealth can call the backend's
// /training/analyze with a log path to get the health analysis.
// Live streaming (WebSocket) is a future feature.

export async function startTraining(req: { model: string; dataset: string; gpu: string }): Promise<{ job_id: string }> {
  await randomDelay()
  return { job_id: `job-${Date.now()}` }
}

export async function getTrainingMetrics(jobId: string): Promise<EpochMetrics[]> {
  await randomDelay()
  return [...MOCK_EPOCH_DATA]
}

// Backend: POST /api/v1/training/analyze returns TrainingAnalysisResult
// which matches this shape. The difference is the backend takes a file path,
// here we're using a job ID (future WebSocket streaming).
export async function getTrainingHealth(jobId: string): Promise<TrainingAnalysisResult> {
  await randomDelay()
  return JSON.parse(JSON.stringify(MOCK_TRAINING_RESULT))
}

export async function stopTraining(jobId: string): Promise<{ status: string }> {
  await delay(500)
  return { status: "stopped" }
}

// ─── Experiments ───

// Backend: no endpoints yet — needs GET/DELETE /api/v1/experiments
// Also needs a persistence layer (MongoDB is configured in settings but not wired).
export async function listExperiments(): Promise<Experiment[]> {
  await randomDelay()
  return [...MOCK_EXPERIMENTS]
}

export async function getExperiment(id: string): Promise<ExperimentDetail> {
  await randomDelay()
  if (id === MOCK_EXPERIMENT_DETAIL.id) {
    return JSON.parse(JSON.stringify(MOCK_EXPERIMENT_DETAIL))
  }
  return JSON.parse(JSON.stringify(MOCK_EXPERIMENT_DETAIL))
}

export async function deleteExperiment(id: string): Promise<{ status: string }> {
  await delay(500)
  return { status: "deleted" }
}

// ─── Settings ───

// Settings are stored in localStorage — no backend needed for this.
// If you want server-side settings persistence later, add GET/PUT /api/v1/settings.
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

// ─── Export (placeholder) ───

export async function exportAnalysis(id: string, format: "pdf" | "json"): Promise<Blob> {
  await delay(1000)
  const data = JSON.stringify(MOCK_ANALYSIS_RESULT, null, 2)
  return new Blob([data], { type: format === "json" ? "application/json" : "application/pdf" })
}
