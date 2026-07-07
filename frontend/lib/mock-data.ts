// ─────────────────────────────────────────────────────────────────
// Mock Data
//
// All data here is fabricated — it does NOT come from the backend.
// The shapes match the backend Pydantic models though, so this file
// doubles as a reference for what the backend should return.
//
// When the backend is connected, this file can be deleted.
// The API client (lib/api.ts) will fetch real data instead.
//
// GPU specs and cloud offerings were copied from the backend's
// knowledge/hardware/gpus.yaml and cloud.yaml — those are real.
// Everything else (experiment history, dashboard stats, training
// metrics, analysis results) is made up for demo purposes.
// ─────────────────────────────────────────────────────────────────

import type {
  GPUSpec, CloudOffering, Recommendation, Warning,
  DatasetAnalysisResult, GPURecommendationResult, GPUCandidate,
  AnalysisResult, DashboardStats, ActivityItem, HealthStatus,
  Experiment, ExperimentDetail, EpochMetrics, TrainingAnalysisResult,
  Settings,
} from "./types"

// ─── GPU Database (from knowledge/hardware/gpus.yaml) ───

export const MOCK_GPUS: GPUSpec[] = [
  { id: "rtx-3060", name: "NVIDIA RTX 3060", vendor: "nvidia", vram_gb: 12, memory_bandwidth_gbps: 360, tflops_fp16: 51, power_watts: 170, training_speed_tier: "mid", architecture: "ampere", msrp_usd: 329 },
  { id: "rtx-4060", name: "NVIDIA RTX 4060", vendor: "nvidia", vram_gb: 8, memory_bandwidth_gbps: 272, tflops_fp16: 49, power_watts: 115, training_speed_tier: "entry", architecture: "ada", msrp_usd: 299 },
  { id: "rtx-4060-ti", name: "NVIDIA RTX 4060 Ti", vendor: "nvidia", vram_gb: 16, memory_bandwidth_gbps: 288, tflops_fp16: 88, power_watts: 165, training_speed_tier: "mid", architecture: "ada", msrp_usd: 399 },
  { id: "rtx-4070", name: "NVIDIA RTX 4070", vendor: "nvidia", vram_gb: 12, memory_bandwidth_gbps: 504, tflops_fp16: 146, power_watts: 200, training_speed_tier: "high", architecture: "ada", msrp_usd: 599 },
  { id: "rtx-4080", name: "NVIDIA RTX 4080", vendor: "nvidia", vram_gb: 16, memory_bandwidth_gbps: 717, tflops_fp16: 97, power_watts: 320, training_speed_tier: "high", architecture: "ada", msrp_usd: 999 },
  { id: "rtx-4090", name: "NVIDIA RTX 4090", vendor: "nvidia", vram_gb: 24, memory_bandwidth_gbps: 1008, tflops_fp16: 165, power_watts: 450, training_speed_tier: "high", architecture: "ada", msrp_usd: 1599 },
  { id: "rtx-5090", name: "NVIDIA RTX 5090", vendor: "nvidia", vram_gb: 32, memory_bandwidth_gbps: 1792, tflops_fp16: 420, power_watts: 575, training_speed_tier: "enthusiast", architecture: "blackwell", msrp_usd: 1999 },
  { id: "rx-7900-xtx", name: "AMD RX 7900 XTX", vendor: "amd", vram_gb: 24, memory_bandwidth_gbps: 960, tflops_fp16: 122, power_watts: 355, training_speed_tier: "high", architecture: "rdna3", msrp_usd: 999 },
  { id: "a100-80gb", name: "NVIDIA A100 80GB", vendor: "nvidia", vram_gb: 80, memory_bandwidth_gbps: 2039, tflops_fp16: 312, power_watts: 400, training_speed_tier: "datacenter", architecture: "ampere", msrp_usd: 15000 },
  { id: "h100-80gb", name: "NVIDIA H100 80GB", vendor: "nvidia", vram_gb: 80, memory_bandwidth_gbps: 3350, tflops_fp16: 756, power_watts: 700, training_speed_tier: "datacenter", architecture: "hopper", msrp_usd: 30000 },
  { id: "mi300x", name: "AMD MI300X", vendor: "amd", vram_gb: 192, memory_bandwidth_gbps: 5300, tflops_fp16: 1307, power_watts: 750, training_speed_tier: "datacenter", architecture: "cdna3", msrp_usd: 15000 },
]

// ─── Cloud Offerings (from knowledge/hardware/cloud.yaml) ───

export const MOCK_CLOUD: CloudOffering[] = [
  { provider_id: "aws", provider_name: "AWS", provider_url: "https://aws.amazon.com/ec2/instance-types/", gpu_id: "a100-80gb", gpu_name: "NVIDIA A100 80GB", instance_type: "p4d.24xlarge", vram_gb: 320, gpu_count: 8, notes: "8x A100 80GB, ideal for large-scale training" },
  { provider_id: "aws", provider_name: "AWS", provider_url: "https://aws.amazon.com/ec2/instance-types/", gpu_id: "h100-80gb", gpu_name: "NVIDIA H100 80GB", instance_type: "p5.48xlarge", vram_gb: 640, gpu_count: 8, notes: "8x H100 80GB, fastest cloud training option" },
  { provider_id: "gcp", provider_name: "Google Cloud", provider_url: "https://cloud.google.com/compute/docs/gpus", gpu_id: "a100-80gb", gpu_name: "NVIDIA A100 80GB", instance_type: "a2-ultragpu-8g", vram_gb: 640, gpu_count: 8, notes: "A2 instances with A100 80GB GPUs" },
  { provider_id: "gcp", provider_name: "Google Cloud", provider_url: "https://cloud.google.com/compute/docs/gpus", gpu_id: "h100-80gb", gpu_name: "NVIDIA H100 80GB", instance_type: "a3-highgpu-8g", vram_gb: 640, gpu_count: 8, notes: "A3 instances with H100 80GB GPUs" },
  { provider_id: "azure", provider_name: "Microsoft Azure", provider_url: "https://azure.microsoft.com/en-us/products/virtual-machines", gpu_id: "a100-80gb", gpu_name: "NVIDIA A100 80GB", instance_type: "NC A100 v4", vram_gb: 80, gpu_count: 1, notes: "Single A100 80GB for mid-scale workloads" },
  { provider_id: "azure", provider_name: "Microsoft Azure", provider_url: "https://azure.microsoft.com/en-us/products/virtual-machines", gpu_id: "h100-80gb", gpu_name: "NVIDIA H100 80GB", instance_type: "ND H100 v5", vram_gb: 640, gpu_count: 8, notes: "8x H100 for enterprise training" },
  { provider_id: "lambda", provider_name: "Lambda Labs", provider_url: "https://lambdalabs.com/service/gpu-cloud", gpu_id: "rtx-4090", gpu_name: "NVIDIA RTX 4090", instance_type: "gpu_1x_rtx4090", vram_gb: 24, gpu_count: 1, notes: "Affordable RTX 4090 for prototyping" },
  { provider_id: "lambda", provider_name: "Lambda Labs", provider_url: "https://lambdalabs.com/service/gpu-cloud", gpu_id: "a100-80gb", gpu_name: "NVIDIA A100 80GB", instance_type: "gpu_8x_a100", vram_gb: 640, gpu_count: 8, notes: "8x A100 SXM4 80GB cluster" },
  { provider_id: "runpod", provider_name: "RunPod", provider_url: "https://www.runpod.io/", gpu_id: "rtx-4090", gpu_name: "NVIDIA RTX 4090", instance_type: "RTX 4090", vram_gb: 24, gpu_count: 1, notes: "On-demand RTX 4090 pods" },
  { provider_id: "runpod", provider_name: "RunPod", provider_url: "https://www.runpod.io/", gpu_id: "rtx-4080", gpu_name: "NVIDIA RTX 4080", instance_type: "RTX 4080", vram_gb: 16, gpu_count: 1, notes: "Budget-friendly 16GB option" },
  { provider_id: "runpod", provider_name: "RunPod", provider_url: "https://www.runpod.io/", gpu_id: "a100-80gb", gpu_name: "NVIDIA A100 80GB", instance_type: "A100 80GB", vram_gb: 80, gpu_count: 1, notes: "Single A100 for fine-tuning large models" },
  { provider_id: "vast", provider_name: "Vast.ai", provider_url: "https://vast.ai/", gpu_id: "rtx-4090", gpu_name: "NVIDIA RTX 4090", instance_type: "RTX 4090", vram_gb: 24, gpu_count: 1, notes: "Marketplace pricing, variable availability" },
]

// ─── Knowledge Engine Recommendations ───

export const MOCK_RECS: Recommendation[] = [
  { rule_id: "pytorch-overfitting-early-stopping", title: "Enable Early Stopping on Validation Loss Plateau", recommendation: "Enable early stopping with patience of 3-5 epochs monitoring validation loss.", reason: "Validation loss increasing while training continues is a strong indicator of overfitting.", confidence: 0.92, priority: 9, category: "training", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/optim.html", references: ["PyTorch Optimizer documentation", "Deep Learning best practices — regularization"], score: 0.92 },
  { rule_id: "pytorch-mixed-precision-amp", title: "Use Automatic Mixed Precision (AMP)", recommendation: "Enable torch.cuda.amp for ~1.5-2x training speedup with minimal accuracy impact.", reason: "AMP uses Tensor Cores on modern NVIDIA GPUs, reducing memory and increasing throughput.", confidence: 0.88, priority: 7, category: "optimization", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/amp.html", references: ["PyTorch AMP documentation"], score: 0.88 },
  { rule_id: "pytorch-dataloader-workers", title: "Increase DataLoader Workers", recommendation: "Increase num_workers in DataLoader and enable pin_memory=True for GPU training.", reason: "Low GPU utilization often indicates a data loading bottleneck.", confidence: 0.85, priority: 6, category: "optimization", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/data.html", references: ["PyTorch DataLoader documentation"], score: 0.85 },
  { rule_id: "cuda-memory-fragmentation", title: "Clear CUDA Cache Between Experiments", recommendation: "Call torch.cuda.empty_cache() and reduce batch size or enable gradient checkpointing.", reason: "VRAM usage above 90% risks OOM errors and fragmentation during training.", confidence: 0.90, priority: 8, category: "hardware", source: "NVIDIA CUDA Documentation", documentation_url: "https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__MEMORY.html", references: ["CUDA Memory Management documentation"], score: 0.90 },
  { rule_id: "hf-gradient-checkpointing", title: "Enable Gradient Checkpointing for Large Models", recommendation: "Enable gradient_checkpointing=True in model config to reduce VRAM by 30-50%.", reason: "Large transformer models exceed consumer GPU VRAM without memory optimization techniques.", confidence: 0.91, priority: 8, category: "optimization", source: "Hugging Face Documentation", documentation_url: "https://huggingface.co/docs/transformers/main/en/perf_train_gpu_one", references: ["Hugging Face training performance guide"], score: 0.91 },
  { rule_id: "hf-flash-attention", title: "Use Flash Attention 2", recommendation: "Install and enable flash-attn for 2-4x attention speedup and reduced memory.", reason: "Flash Attention reduces memory complexity from O(n²) to O(n) for sequence length n.", confidence: 0.89, priority: 7, category: "optimization", source: "Hugging Face Documentation", documentation_url: "https://huggingface.co/docs/transformers/main/en/perf_infer_gpu_one", references: ["Flash Attention paper", "Hugging Face transformers performance docs"], score: 0.89 },
  { rule_id: "deepspeed-zero-stage2", title: "Use ZeRO Stage 2 for Multi-GPU Training", recommendation: "Configure DeepSpeed ZeRO Stage 2 to shard optimizer states across GPUs.", reason: "ZeRO Stage 2 reduces per-GPU memory by partitioning optimizer states, enabling larger models.", confidence: 0.90, priority: 8, category: "optimization", source: "DeepSpeed Documentation", documentation_url: "https://www.deepspeed.ai/docs/config-json/", references: ["DeepSpeed ZeRO paper", "DeepSpeed configuration guide"], score: 0.90 },
  { rule_id: "rocm-miopen-tuning", title: "Enable MIOpen Find Mode for Convolution Tuning", recommendation: "Set MIOPEN_FIND_MODE=1 for automatic convolution algorithm selection on AMD GPUs.", reason: "MIOpen find mode benchmarks convolution algorithms and selects the fastest for your workload.", confidence: 0.83, priority: 6, category: "optimization", source: "AMD ROCm Documentation", documentation_url: "https://rocm.docs.amd.com/projects/MIOpen/en/latest/", references: ["MIOpen convolution documentation"], score: 0.83 },
]

export const MOCK_WARNINGS: Warning[] = [
  { rule_id: "hardware-vram-insufficient", title: "Insufficient VRAM for Model Size", message: "Models requiring more than 8GB VRAM will not fit on consumer entry-level GPUs.", confidence: 0.85, source: "NVIDIA CUDA Documentation", documentation_url: "https://docs.nvidia.com/cuda/cuda-c-programming-guide/" },
  { rule_id: "hardware-large-model-multi-gpu", title: "Use Multi-GPU or Model Parallelism", message: "Models requiring 40GB+ VRAM exceed single consumer GPU capacity.", confidence: 0.90, source: "DeepSpeed Documentation", documentation_url: "https://www.deepspeed.ai/tutorials/zero/" },
]

// ─── Dataset Recommendations ───

export const MOCK_DATASET_RECS: Recommendation[] = [
  { rule_id: "dataset-class-imbalance", title: "Address Class Imbalance", recommendation: "Use weighted CrossEntropyLoss, oversampling minority classes, or focal loss.", reason: "Severe class imbalance causes models to bias toward majority classes, hurting minority recall.", confidence: 0.88, priority: 8, category: "dataset", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/nn.html#torch.nn.CrossEntropyLoss", references: ["Focal Loss paper"], score: 0.88 },
  { rule_id: "dataset-duplicates", title: "Remove Duplicate Images", recommendation: "Run deduplication using perceptual hashing before training to prevent data leakage.", reason: "Duplicate images in train/val splits inflate metrics and cause overfitting.", confidence: 0.86, priority: 7, category: "dataset", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/vision/stable/index.html", references: ["Dataset quality best practices"], score: 0.86 },
  { rule_id: "dataset-small", title: "Increase Dataset Size", recommendation: "Use data augmentation, synthetic data generation, or collect more samples.", reason: "Small datasets increase overfitting risk and limit model generalization.", confidence: 0.80, priority: 6, category: "dataset", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/vision/stable/transforms.html", references: ["Data augmentation best practices"], score: 0.80 },
]

export const MOCK_DATASET_WARNINGS: Warning[] = [
  { rule_id: "dataset-class-imbalance", title: "Class Imbalance Detected", message: "Class imbalance ratio is 8:1. Consider weighted loss or oversampling.", confidence: 0.88, source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/nn.html#torch.nn.CrossEntropyLoss" },
]

// ─── Mock GPU Recommendation Result ───

export const MOCK_GPU_RESULT: GPURecommendationResult = {
  required_vram_gb: 18.5,
  candidates: [
    { gpu: MOCK_GPUS[10], score: 0.95, fit_rating: "excellent", vram_utilization: 0.10, headroom_gb: 173.5, reasons: ["Good VRAM fit — efficient utilization", "ROCm support — verify framework compatibility"] },
    { gpu: MOCK_GPUS[9], score: 0.89, fit_rating: "excellent", vram_utilization: 0.23, headroom_gb: 61.5, reasons: ["Good VRAM fit — efficient utilization", "Full CUDA ecosystem support"] },
    { gpu: MOCK_GPUS[8], score: 0.84, fit_rating: "excellent", vram_utilization: 0.23, headroom_gb: 61.5, reasons: ["Good VRAM fit — efficient utilization", "Full CUDA ecosystem support"] },
    { gpu: MOCK_GPUS[6], score: 0.78, fit_rating: "good", vram_utilization: 0.58, headroom_gb: 13.5, reasons: ["Good VRAM fit — efficient utilization", "Full CUDA ecosystem support"] },
    { gpu: MOCK_GPUS[5], score: 0.72, fit_rating: "tight", vram_utilization: 0.77, headroom_gb: 5.5, reasons: ["Tight VRAM fit — limited headroom for larger batches", "Full CUDA ecosystem support"] },
  ],
  best_pick: { gpu: MOCK_GPUS[10], score: 0.95, fit_rating: "excellent", vram_utilization: 0.10, headroom_gb: 173.5, reasons: ["Good VRAM fit — efficient utilization", "ROCm support — verify framework compatibility"] },
  cloud_offerings: [
    MOCK_CLOUD[0], MOCK_CLOUD[2], MOCK_CLOUD[4],
  ],
  warnings: MOCK_WARNINGS,
  knowledge_recommendations: MOCK_RECS.slice(4, 8),
  sources: ["AMD ROCm Documentation", "NVIDIA CUDA Documentation", "DeepSpeed Documentation", "Hugging Face Documentation"],
}

// ─── Mock Dataset Analysis ───

export const MOCK_DATASET_RESULT: DatasetAnalysisResult = {
  metrics: {
    image_count: 12500,
    class_count: 10,
    class_distribution: { cat: 1500, dog: 1500, bird: 1200, fish: 1000, car: 1400, truck: 1300, boat: 1100, plane: 900, horse: 850, frog: 1750 },
    class_stats: [
      { name: "frog", count: 1750, percent: 14.0 },
      { name: "cat", count: 1500, percent: 12.0 },
      { name: "dog", count: 1500, percent: 12.0 },
      { name: "car", count: 1400, percent: 11.2 },
      { name: "truck", count: 1300, percent: 10.4 },
      { name: "bird", count: 1200, percent: 9.6 },
      { name: "boat", count: 1100, percent: 8.8 },
      { name: "fish", count: 1000, percent: 8.0 },
      { name: "plane", count: 900, percent: 7.2 },
      { name: "horse", count: 850, percent: 6.8 },
    ],
    class_imbalance_ratio: 2.1,
    duplicate_count: 375,
    duplicate_percent: 3.0,
    near_duplicate_count: 120,
    blur_count: 625,
    blur_percent: 5.0,
    missing_label_count: 250,
    missing_label_percent: 2.0,
    median_resolution: 256,
    min_resolution: 128,
    max_resolution: 1024,
    avg_resolution: 312.5,
  },
  score: 82,
  grade: "B",
  warnings: MOCK_DATASET_WARNINGS,
  recommendations: MOCK_DATASET_RECS,
  accuracy_impact: {
    estimated_loss_percent: 4.5,
    confidence: 0.78,
    factors: ["3% duplicate images may cause data leakage", "5% blurry images reduce feature quality", "Class imbalance ratio of 2.1:1 may bias toward majority classes"],
  },
  sources: ["PyTorch Documentation"],
}

// ─── Mock Analysis Result (Pre-Training) ───

export const MOCK_ANALYSIS_RESULT: AnalysisResult = {
  predictions: {
    estimated_cost_usd: 12.50,
    estimated_runtime_hours: 4.5,
    peak_vram_gb: 18.5,
    oom_probability: 0.08,
    convergence_probability: 0.78,
    expected_accuracy_min: 0.85,
    expected_accuracy_max: 0.89,
    gpu_utilization_estimate: 0.82,
    carbon_footprint_kg: 2.3,
    bottlenecks: ["Data loading (CPU bottleneck expected with current worker count)"],
  },
  recommendations: [
    MOCK_RECS[1], // AMP
    MOCK_RECS[4], // Gradient checkpointing
    MOCK_RECS[5], // Flash attention
    { rule_id: "custom-batch-size", title: "Increase Batch Size", recommendation: "Current batch size of 4 underutilizes GPU memory. Increase to 8 for better throughput.", reason: "VRAM utilization is only 23% with current batch size.", confidence: 0.85, priority: 7, category: "optimization", source: "PreFlight Analysis", documentation_url: "", references: [], score: 0.85 },
  ],
  warnings: [],
  explanation: {
    summary: "Your 7B transformer fine-tune is well-configured but has room for optimization. The main bottleneck is data loading, and batch size is underutilizing GPU memory.",
    reasoning: [
      { factor: "Dataset size (2M samples)", impact: "Primary driver of 4.5h runtime. Each epoch processes all samples." },
      { factor: "Batch size (4)", impact: "Underutilizes GPU memory (23% VRAM). Increasing to 8 would reduce runtime by ~40%." },
      { factor: "LoRA mode", impact: "Reduces VRAM by 75% vs full fine-tune. Good choice for 7B model." },
      { factor: "FP16 precision", impact: "Halves memory vs FP32. Consider BF16 for better numerical stability on AMD GPUs." },
    ],
    recommendations_savings: "Applying all recommendations could reduce runtime by ~40% (4.5h → 2.7h) and cost by ~35% ($12.50 → $8.10), saving approximately $4.40.",
    action_checklist: [
      "Increase batch size from 4 to 8",
      "Enable BF16 mixed precision (torch.cuda.amp)",
      "Increase DataLoader workers to 8 and enable pin_memory",
      "Use cosine learning rate scheduler with warmup",
      "Enable Flash Attention 2 if using Hugging Face Transformers",
    ],
  },
  sources: ["PyTorch Documentation", "Hugging Face Documentation", "PreFlight Prediction Engine"],
}

// ─── Mock Dashboard ───

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  total_analyses: 47,
  active_jobs: 2,
  datasets_analyzed: 12,
  avg_savings: 32.5,
}

export const MOCK_ACTIVITY: ActivityItem[] = [
  { id: "1", type: "analysis", title: "Analysis completed", description: "7B Transformer LoRA fine-tune — 78% convergence probability", timestamp: new Date(Date.now() - 1000 * 60 * 15).toISOString() },
  { id: "2", type: "training", title: "Training started", description: "ResNet-50 on ImageNet subset — Epoch 3/20", timestamp: new Date(Date.now() - 1000 * 60 * 45).toISOString() },
  { id: "3", type: "dataset", title: "Dataset analyzed", description: "CIFAR-10 augmentation set — Score 82/100 (B)", timestamp: new Date(Date.now() - 1000 * 60 * 120).toISOString() },
  { id: "4", type: "gpu", title: "GPU recommended", description: "AMD MI300X for 13B full fine-tune — Excellent fit", timestamp: new Date(Date.now() - 1000 * 60 * 240).toISOString() },
  { id: "5", type: "analysis", title: "Analysis completed", description: "Vision CNN on medical imaging — OOM risk 12%", timestamp: new Date(Date.now() - 1000 * 60 * 360).toISOString() },
]

export const MOCK_HEALTH: HealthStatus = {
  status: "ok",
  version: "0.1.0",
  rules_loaded: 30,
}

// ─── Mock Training Data ───

export const MOCK_EPOCH_DATA: EpochMetrics[] = Array.from({ length: 20 }, (_, i) => {
  const epoch = i + 1
  const trainLoss = Math.max(0.1, 2.3 * Math.exp(-0.15 * epoch) + (Math.random() - 0.5) * 0.05)
  const valLoss = epoch < 12
    ? Math.max(0.15, 2.5 * Math.exp(-0.12 * epoch) + (Math.random() - 0.5) * 0.05)
    : Math.max(0.15, 2.5 * Math.exp(-0.12 * 12) + (epoch - 12) * 0.08 + (Math.random() - 0.5) * 0.03)
  const accuracy = Math.min(0.95, 0.3 + 0.6 * (1 - Math.exp(-0.2 * epoch)) + (Math.random() - 0.5) * 0.02)
  return {
    epoch,
    train_loss: parseFloat(trainLoss.toFixed(4)),
    val_loss: parseFloat(valLoss.toFixed(4)),
    accuracy: parseFloat(accuracy.toFixed(4)),
    gpu_utilization: 75 + Math.random() * 15,
    cpu_utilization: 35 + Math.random() * 10,
    vram_gb: 18.2 + Math.random() * 0.5,
    vram_percent: 76 + Math.random() * 3,
    power_watts: 340 + Math.random() * 20,
  }
})

export const MOCK_TRAINING_RESULT: TrainingAnalysisResult = {
  metrics: {
    epoch_count: 20,
    current_epoch: 20,
    latest_train_loss: 0.12,
    latest_val_loss: 0.45,
    best_val_loss: 0.28,
    best_epoch: 12,
    validation_loss_increasing: true,
    train_loss_stagnant: false,
    overfitting_gap: 0.33,
    overfitting_detected: true,
    loss_diverging: false,
    accuracy_plateau: true,
    gpu_utilization: 82,
    cpu_utilization: 38,
    avg_gpu_utilization: 81,
    vram_usage_percent: 78,
    vram_near_limit: false,
  },
  trends: [
    { name: "overfitting", description: "Validation loss has been increasing for 8 epochs while training loss continues to decrease.", severity: "high", epochs_affected: [13, 14, 15, 16, 17, 18, 19, 20] },
    { name: "accuracy_plateau", description: "Accuracy improved less than 0.5% over the last 5 epochs.", severity: "medium", epochs_affected: [16, 17, 18, 19, 20] },
  ],
  score: 65,
  grade: "D",
  warnings: [
    { rule_id: "pytorch-overfitting-early-stopping", title: "Possible Overfitting", message: "Validation loss increasing for 8+ epochs. Consider early stopping.", confidence: 0.92, source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/optim.html" },
  ],
  recommendations: [
    MOCK_RECS[0], // Early stopping
    { rule_id: "training-overfitting-gap", title: "Train/Validation Loss Gap Detected", recommendation: "Add dropout, weight decay, or data augmentation to reduce overfitting.", reason: "Large gap between training and validation loss indicates the model is memorizing training data.", confidence: 0.90, priority: 8, category: "training", source: "PyTorch Documentation", documentation_url: "https://pytorch.org/docs/stable/nn.html", references: ["Regularization best practices"], score: 0.90 },
  ],
  sources: ["PyTorch Documentation"],
}

// ─── Mock Experiments ───

export const MOCK_EXPERIMENTS: Experiment[] = [
  { id: "exp-001", name: "7B Llama LoRA Fine-Tune", model: "Llama-2-7B", dataset: "Custom instruction set", gpu: "RTX 4090", status: "completed", runtime_hours: 4.2, cost_usd: 11.80, accuracy: 0.87, date: "2026-07-06T14:30:00Z" },
  { id: "exp-002", name: "ResNet-50 ImageNet", model: "ResNet-50", dataset: "ImageNet-1K (subset)", gpu: "A100 80GB", status: "completed", runtime_hours: 12.5, cost_usd: 45.20, accuracy: 0.92, date: "2026-07-05T09:15:00Z" },
  { id: "exp-003", name: "ViT-Base Fine-Tune", model: "ViT-Base/16", dataset: "CIFAR-100", gpu: "RTX 4090", status: "completed", runtime_hours: 2.1, cost_usd: 5.40, accuracy: 0.88, date: "2026-07-05T16:00:00Z" },
  { id: "exp-004", name: "13B Full Fine-Tune", model: "Llama-2-13B", dataset: "Alpaca clean", gpu: "MI300X", status: "running", runtime_hours: 8.0, cost_usd: 96.00, accuracy: null, date: "2026-07-07T08:00:00Z" },
  { id: "exp-005", name: "BERT-Base SQuAD", model: "BERT-Base", dataset: "SQuAD v2", gpu: "RTX 4080", status: "failed", runtime_hours: 1.2, cost_usd: 2.80, accuracy: null, date: "2026-07-04T11:30:00Z" },
  { id: "exp-006", name: "GPT-2 Medium LoRA", model: "GPT-2 Medium", dataset: "WikiText-103", gpu: "RTX 4070", status: "stopped", runtime_hours: 3.5, cost_usd: 7.20, accuracy: 0.71, date: "2026-07-03T18:45:00Z" },
  { id: "exp-007", name: "EfficientNet-B0 Transfer", model: "EfficientNet-B0", dataset: "Flowers-102", gpu: "RTX 4060 Ti", status: "completed", runtime_hours: 1.8, cost_usd: 3.60, accuracy: 0.94, date: "2026-07-02T20:00:00Z" },
  { id: "exp-008", name: "T5-Small Summarization", model: "T5-Small", dataset: "CNN/DailyMail", gpu: "A100 80GB", status: "completed", runtime_hours: 6.3, cost_usd: 22.80, accuracy: 0.81, date: "2026-07-02T10:00:00Z" },
]

export const MOCK_EXPERIMENT_DETAIL: ExperimentDetail = {
  ...MOCK_EXPERIMENTS[0],
  predictions: {
    estimated_cost_usd: 12.50,
    estimated_runtime_hours: 4.5,
    peak_vram_gb: 18.5,
    oom_probability: 0.08,
    convergence_probability: 0.78,
    expected_accuracy_min: 0.85,
    expected_accuracy_max: 0.89,
    gpu_utilization_estimate: 0.82,
    carbon_footprint_kg: 2.3,
    bottlenecks: ["Data loading"],
  },
  actuals: {
    runtime_hours: 4.2,
    cost_usd: 11.80,
    accuracy: 0.87,
    converged: true,
  },
  recommendations_applied: ["Enabled BF16 mixed precision", "Increased batch size to 8", "Used cosine LR scheduler with warmup"],
  notes: "Training converged at epoch 18. Final validation accuracy within predicted range. Cost was 6% lower than predicted due to faster-than-expected convergence.",
}

// ─── Default Settings ───

export const DEFAULT_SETTINGS: Settings = {
  backend_url: "http://localhost:8000",
  api_key: "",
  default_vendor: "any",
  default_precision: "fp16",
  default_budget: "any",
  theme: "dark",
  cost_unit: "USD",
  runtime_unit: "hours",
  notify_training_complete: true,
  notify_anomaly: true,
}
