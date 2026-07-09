# GPU Training Benchmarks

Preflight calibrates its training-time (and therefore cost) estimates using
**measured relative training throughput** rather than raw peak TFLOPS. Peak
TFLOPS overstates real performance because actual training speed is bounded by
memory bandwidth, tensor-core utilization (MFU), interconnect, and software
maturity (CUDA vs ROCm).

## Where the data lives

`knowledge/hardware/benchmarks.yaml`

```yaml
metadata:
  reference_gpu_id: a100-80gb
  reference_throughput: 1.0
gpus:
  h100-80gb:
    relative_training_throughput: 2.3   # ~2.1-2.5x an A100 for transformer training
    typical_mfu_percent: 55
    source: "Measured LLM training tok/s + MLPerf BF16"
    approximate: true
```

`relative_training_throughput` is normalized to the reference GPU (A100 80GB = 1.0).
A value of `2.4` means the GPU trains ~2.4x faster than an A100 on a comparable
workload.

## How it feeds the cost calculator

`CostCalculator._speed_factor()`:

1. Look up measured `relative_training_throughput` for the GPU and the reference GPU.
2. If both exist: `speed_factor = ref_throughput / gpu_throughput` (higher throughput -> fewer seconds/epoch).
3. If missing: fall back to the peak-TFLOPS ratio (`ref_tflops / gpu.tflops_fp16`).

The result includes a note telling you which path was used, e.g.:

- `Training speed from approx. benchmark (MLPerf / CoreWeave).`
- `Training speed estimated from peak TFLOPS (no benchmark data).`

## Sources

| Source | Use |
| --- | --- |
| [MLPerf Training](https://mlcommons.org/benchmarks/training/) | Time-to-train anchors (primary); v5.0 added MI300X + RX 7900 XTX |
| [Lambda GPU benchmarks](https://lambda.ai/gpu-benchmarks) | Per-GPU training throughput methodology |
| [BestGPUCloud H100/A100/4090 tok/s](https://www.bestgpucloud.com/en/blog/nvidia-h100-vs-a100-vs-rtx-4090-ai-gpu) | Measured LLM training tokens/sec (H100/A100/4090) |
| [Thunder Compute A100 vs H100](https://www.thundercompute.com/blog/nvidia-a100-vs-h100) | BF16 training speedup (2.15x) |
| [SemiAnalysis MI300X vs H100](https://newsletter.semianalysis.com/p/mi300x-vs-h100-vs-h200-benchmark-part-1-training) | MI300X training parity + ROCm caveats |
| [CoreWeave H100 at scale](https://www.coreweave.com/blog/nvidia-h100-gpu-benchmark-results-what-we-learned-from-large-scale-gpu-testing) | H100 vs A100 real-world scaling |

## Data quality caveat

Entries marked `approximate: true` are **landscape estimates** derived from the
published benchmarks above — not exact per-model MLPerf submissions. They are far
better than a pure TFLOPS ratio, but for production accuracy replace them with
scraped MLPerf time-to-train figures for your specific model/precision. The schema
is intentionally stable so real numbers can be dropped in without code changes.
