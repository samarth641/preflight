// Type definitions — mirror backend Pydantic models EXACTLY
// DO NOT change field names or types without explicit instruction
// Updated 2026-07-09 to match backend @ dda968c

// ─── Engine Models (app/core/engine/models.py) ───

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

// ─── GPU Models (app/core/recommenders/gpu/models.py) ───

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

export interface GPURecommendationRequest {
  parameter_count_billion: number
  batch_size: number
  precision: Precision
  training_mode: TrainingMode
  model_type: ModelType
  image_size: number
  sequence_length: number
  budget_tier: BudgetTier | null
  preferred_vendor: Vendor | null
  max_results: number
  include_cloud: boolean
  include_cost: boolean
  epochs: number
  dataset_samples: number
  dataset_size_gb: number | null
  deployment: DeploymentType
}

export interface GPUCandidate {
  gpu: GPUSpec
  score: number
  fit_rating: FitRating
  vram_utilization: number
  headroom_gb: number
  reasons: string[]
  cost_estimate: CostEstimateResult | null
}

export interface GPURecommendationResult {
  required_vram_gb: number
  request: GPURecommendationRequest
  candidates: GPUCandidate[]
  best_pick: GPUCandidate | null
  cloud_offerings: CloudOffering[]
  warnings: Warning[]
  knowledge_recommendations: Recommendation[]
  sources: string[]
  cheapest_gpu: GPUCandidate | null
}

// ─── Dataset Models (app/core/analyzers/dataset/models.py) ───

export type DatasetLayout = "class_folders" | "flat" | "mixed"

export interface ClassStats {
  name: string
  count: number
  percent: number
}

export interface DatasetMetrics {
  image_count: number
  class_count: number
  layout: DatasetLayout
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
  dataset_path: string | null
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

// ─── Training Log Models (app/core/analyzers/training/models.py) ───

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

export interface TrainingTrend {
  name: string
  description: string
  severity: string
  epochs_affected: number[]
}

export interface TrainingAnalysisResult {
  log_path: string | null
  metrics: TrainingMetrics
  trends: TrainingTrend[]
  score: number
  grade: string
  warnings: Warning[]
  recommendations: Recommendation[]
  sources: string[]
}

// ─── Cost Models (app/core/calculators/cost/models.py) ───

export type DeploymentType = "local" | "cloud"

export interface CostBreakdown {
  cloud_usd: number
  electricity_usd: number
  storage_usd: number
  bandwidth_usd: number
  hardware_amortization_usd: number
}

export interface CostEstimateRequest {
  parameter_count_billion: number
  gpu_id: string
  epochs: number
  dataset_samples: number
  dataset_size_gb: number | null
  batch_size: number
  model_type: ModelType
  deployment: DeploymentType
  cloud_provider: string | null
  electricity_usd_per_kwh: number | null
  gpu_count: number
}

export interface CostEstimateResult {
  gpu_id: string
  gpu_name: string
  deployment: DeploymentType
  cloud_provider: string | null
  estimated_hours: number
  estimated_days: number
  gpu_hours: number
  seconds_per_epoch: number
  breakdown: CostBreakdown
  total_usd: number
  hourly_rate_usd: number | null
  notes: string[]
}

// ─── Duration Prediction (app/schemas/predict.py) ───

export type Domain = "language" | "vision" | "multimodal" | "image generation" | "biology" | "other"

export interface DurationPredictRequest {
  parameter_count_billion: number
  dataset_tokens: number
  gpu_id: string
  n_gpus: number
  epochs: number
  domain: Domain
  cloud_provider: string | null
}

export interface DurationPredictResult {
  estimated_hours: number
  estimated_duration_human: string
  theoretical_hours: number
  gpu_id: string
  n_gpus: number
  model_version: string
  estimated_cost_usd: number | null
  cost_provider: string | null
  hourly_rate_usd: number | null
}

// ─── Monitor Models (app/core/monitors/training/models.py) ───

export interface ExperimentRecord {
  id: string
  name: string
  model: string
  params_million: number
  dataset: string
  status: string  // running | completed | failed
  gpu: string
  total_epochs: number
  epochs_completed: number
  final_accuracy: number | null
  best_val_loss: number | null
  convergence: string | null  // converged | plateau | diverging | running
  duration_hours: number | null
  started_at: string
  target_accuracy: number | null
}

export interface EpochPoint {
  epoch: number
  train_loss: number | null
  val_loss: number | null
  accuracy: number | null
  gpu_utilization: number | null
}

export interface LiveTrainingMonitor {
  experiment_id: string
  experiment_name: string
  status: string
  params_million: number
  epoch: number
  total_epochs: number
  epoch_progress_percent: number
  samples_seen_million: number
  train_loss: number | null
  val_loss: number | null
  accuracy: number | null
  gpu_utilization: number | null
  convergence_status: string  // training | converged | plateau | stagnant | diverging
  health_score: number
  health_grade: string
  curve: EpochPoint[]
  warnings: Warning[]
  recommendations: Recommendation[]
}

export interface DashboardStats {
  total_experiments: number
  running: number
  completed: number
  failed: number
  experiments_100m: number
  avg_accuracy: number | null
  best_accuracy: number | null
  total_gpu_hours: number
  convergence_rate_percent: number
  active_experiment_id: string | null
}

export interface ExperimentHistoryResponse {
  experiments: ExperimentRecord[]
  active_experiment_id: string | null
}

// ─── GPU Benchmark (knowledge/hardware/benchmarks.yaml) ───

export interface GPUBenchmark {
  relative_training_throughput: number
  typical_mfu_percent: number
  source: string
  approximate: boolean
}

// ─── Health (app/schemas/common.py) ───

export interface HealthStatus {
  status: string
  version: string
}

// ─── Pre-Training Analysis (PLACEHOLDER — no backend endpoint) ───
// These fields have NO backend support. Kept for UI continuity.
// Will be removed or replaced when backend adds a /analyze endpoint.

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

// NOTE: PredictionResult fields below are PLACEHOLDER predictions.
// The backend does NOT implement these — only duration + cost exist.
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

// ─── Activity (frontend-only — no backend endpoint) ───

export interface ActivityItem {
  id: string
  type: "analysis" | "dataset" | "training" | "gpu"
  title: string
  description: string
  timestamp: string
}

// ─── Settings (frontend-only — localStorage) ───

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
