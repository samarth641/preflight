// ─────────────────────────────────────────────────────────────────
// Type Definitions
//
// These mirror the backend Pydantic models. If you change a model
// on the backend side, update the matching interface here so the
// frontend stays in sync.
//
// Backend models live in:
//   backend/app/core/engine/models.py        — Recommendation, Warning
//   backend/app/core/recommenders/gpu/models.py — GPU models
//   backend/app/core/analyzers/dataset/models.py — Dataset models
//   backend/app/core/analyzers/training/models.py — Training models
//   backend/app/core/calculators/cost/models.py — Cost models
//   backend/app/schemas/                     — API request/response schemas
// ─────────────────────────────────────────────────────────────────

// ─── Engine Models ───

export interface Recommendation {
  rule_id: string
  title: string
  recommendation: string
  reason: string
  confidence: number
  priority: number
  category: string
  source: string
  documentation_url: string
  references: string[]
  score: number
}

export interface Warning {
  rule_id: string
  title: string
  message: string
  confidence: number
  source: string
  documentation_url: string
}

// ─── GPU Models ───

export type Vendor = "nvidia" | "amd"
export type TrainingMode = "full" | "lora" | "inference"
export type ModelType = "vision" | "cnn" | "transformer"
export type Precision = "fp32" | "fp16" | "int8"
export type BudgetTier = "entry" | "mid" | "high" | "enthusiast" | "datacenter"
export type FitRating = "excellent" | "good" | "tight" | "overkill" | "insufficient"

export interface GPUSpec {
  id: string
  name: string
  vendor: Vendor
  vram_gb: number
  memory_bandwidth_gbps: number
  tflops_fp16: number
  power_watts: number
  training_speed_tier: string
  architecture: string
  msrp_usd: number | null
}

export interface CloudOffering {
  provider_id: string
  provider_name: string
  provider_url: string
  gpu_id: string
  gpu_name: string
  instance_type: string
  vram_gb: number
  gpu_count: number
  notes: string
}

export interface GPUCandidate {
  gpu: GPUSpec
  score: number
  fit_rating: FitRating
  vram_utilization: number
  headroom_gb: number
  reasons: string[]
}

export interface GPURecommendationRequest {
  parameter_count_billion: number
  batch_size: number
  precision: Precision
  training_mode: TrainingMode
  model_type: ModelType
  image_size?: number
  sequence_length?: number
  budget_tier?: BudgetTier | null
  preferred_vendor?: Vendor | null
  max_results?: number
  include_cloud?: boolean
}

export interface GPURecommendationResult {
  required_vram_gb: number
  candidates: GPUCandidate[]
  best_pick: GPUCandidate | null
  cloud_offerings: CloudOffering[]
  warnings: Warning[]
  knowledge_recommendations: Recommendation[]
  sources: string[]
}

// ─── Dataset Models ───

export interface ClassStats {
  name: string
  count: number
  percent: number
}

export interface DatasetMetrics {
  image_count: number
  class_count: number
  class_distribution: Record<string, number>
  class_stats: ClassStats[]
  class_imbalance_ratio: number
  duplicate_count: number
  duplicate_percent: number
  near_duplicate_count: number
  blur_count: number
  blur_percent: number
  missing_label_count: number
  missing_label_percent: number
  median_resolution: number
  min_resolution: number
  max_resolution: number
  avg_resolution: number
}

export interface AccuracyImpact {
  estimated_loss_percent: number
  confidence: number
  factors: string[]
}

export interface DatasetAnalysisResult {
  metrics: DatasetMetrics
  score: number
  grade: string
  warnings: Warning[]
  recommendations: Recommendation[]
  accuracy_impact: AccuracyImpact
  sources: string[]
}

export interface DatasetManualInput {
  image_count: number
  class_count: number
  class_imbalance_ratio: number
  duplicate_percent: number
  blur_percent: number
  missing_label_percent: number
  median_resolution: number
}

// ─── Training Models (PLACEHOLDER) ───

export interface EpochMetrics {
  epoch: number
  train_loss: number | null
  val_loss: number | null
  accuracy: number | null
  gpu_utilization: number | null
  cpu_utilization: number | null
  vram_gb: number | null
  vram_percent: number | null
  power_watts: number | null
}

export interface TrainingTrend {
  name: string
  description: string
  severity: "low" | "medium" | "high"
  epochs_affected: number[]
}

export interface TrainingMetrics {
  epoch_count: number
  current_epoch: number
  latest_train_loss: number | null
  latest_val_loss: number | null
  best_val_loss: number | null
  best_epoch: number | null
  validation_loss_increasing: boolean
  train_loss_stagnant: boolean
  overfitting_gap: number
  overfitting_detected: boolean
  loss_diverging: boolean
  accuracy_plateau: boolean
  gpu_utilization: number | null
  cpu_utilization: number | null
  avg_gpu_utilization: number | null
  vram_usage_percent: number | null
  vram_near_limit: boolean
}

export interface TrainingAnalysisResult {
  metrics: TrainingMetrics
  trends: TrainingTrend[]
  score: number
  grade: string
  warnings: Warning[]
  recommendations: Recommendation[]
  sources: string[]
}

// ─── Prediction Models (PLACEHOLDER) ───

export interface AnalysisRequest {
  model_type: ModelType
  parameter_count_billion: number
  training_mode: TrainingMode
  precision: Precision
  batch_size: number
  learning_rate: number
  optimizer: string
  scheduler: string
  epochs: number
  sequence_length?: number
  image_size?: number
  dataset_size: number
  gpu_id?: string
}

export interface PredictionResult {
  estimated_cost_usd: number
  estimated_runtime_hours: number
  peak_vram_gb: number
  oom_probability: number
  convergence_probability: number
  expected_accuracy_min: number
  expected_accuracy_max: number
  gpu_utilization_estimate: number
  carbon_footprint_kg: number
  bottlenecks: string[]
}

export interface Explanation {
  summary: string
  reasoning: { factor: string; impact: string }[]
  recommendations_savings: string
  action_checklist: string[]
}

export interface AnalysisResult {
  predictions: PredictionResult
  recommendations: Recommendation[]
  warnings: Warning[]
  explanation: Explanation
  sources: string[]
}

// ─── Dashboard Models ───

export interface DashboardStats {
  total_analyses: number
  active_jobs: number
  datasets_analyzed: number
  avg_savings: number
}

export interface ActivityItem {
  id: string
  type: "analysis" | "dataset" | "training" | "gpu"
  title: string
  description: string
  timestamp: string
}

export interface HealthStatus {
  status: "ok" | "degraded" | "error"
  version: string
  rules_loaded: number
}

// ─── Experiment Models (PLACEHOLDER) ───

export type ExperimentStatus = "completed" | "failed" | "stopped" | "running"

export interface Experiment {
  id: string
  name: string
  model: string
  dataset: string
  gpu: string
  status: ExperimentStatus
  runtime_hours: number
  cost_usd: number
  accuracy: number | null
  date: string
}

export interface ExperimentDetail extends Experiment {
  predictions: PredictionResult
  actuals: {
    runtime_hours: number
    cost_usd: number
    accuracy: number | null
    converged: boolean
  }
  recommendations_applied: string[]
  notes: string
}

// ─── Settings ───

export interface Settings {
  backend_url: string
  api_key: string
  default_vendor: Vendor | "any"
  default_precision: Precision
  default_budget: BudgetTier | "any"
  theme: "dark"
  cost_unit: "USD" | "EUR"
  runtime_unit: "hours" | "minutes"
  notify_training_complete: boolean
  notify_anomaly: boolean
}
