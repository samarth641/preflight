# Preflight

AI Training Intelligence Platform — a rule-based expert system for ML training recommendations.

## Status

**Phase 1 complete:** Foundation architecture, knowledge engine, rule loader, and plugin system.

**Phase 2 complete:** Dataset Analyzer, GPU Recommender.

## Quick Start

```bash
cd backend
pip install -e ".[dev]"
trainwise doctor
trainwise analyze-dataset /path/to/your/dataset
trainwise recommend-gpu --params-billion 7 --mode lora --type transformer
pytest ../tests -v
```

## Architecture

```
preflight/
├── backend/          # FastAPI + Knowledge Engine
├── frontend/         # Next.js dashboard (future)
├── knowledge/        # YAML rule knowledge base
├── packages/         # Shared packages (future)
├── docs/             # Documentation
└── tests/            # Test suite
```

See [docs/architecture.md](docs/architecture.md) for full system design.

---

## Dataset Analyzer

Scans an image folder, checks quality, scores it, and returns rule-based recommendations.

### How it works

1. **Scan** — Finds images (`.jpg`, `.png`, `.tif`, etc.). Class subfolders (`cats/`, `dogs/`) are used as labels.
2. **Per-image checks** — Resolution, blur (edge sharpness), exact duplicates (MD5), near-duplicates (perceptual hash).
3. **Metrics** — Image count, class balance, duplicate %, blur %, missing labels %, resolution stats.
4. **Score (0–100)** — Starts at 100, subtracts for imbalance, duplicates, blur, low resolution, small size → grade A–F.
5. **Rule engine** — Metrics sent to `knowledge/datasets/quality.yaml` → warnings + recommendations.
6. **Output** — Score, metrics, recommendations, estimated accuracy impact.

### CLI usage

```bash
# Analyze a class-folder dataset
trainwise analyze-dataset "F:\path\to\dataset"

# Limit scan on large datasets
trainwise analyze-dataset "F:\path\to\dataset" --max-images 1000

# JSON or Markdown output
trainwise analyze-dataset "F:\path\to\dataset" --format json
trainwise analyze-dataset "F:\path\to\dataset" --format markdown
```

### Expected folder layout

```
my_dataset/
├── cats/
│   ├── cat_001.jpg
│   └── cat_002.jpg
└── dogs/
    └── dog_001.jpg
```

### Python API

```python
from app.core.analyzers import DatasetAnalyzer

result = DatasetAnalyzer().analyze("/path/to/dataset")
print(result.score, result.grade)
print(result.metrics.class_imbalance_ratio)
for rec in result.recommendations:
    print(rec.recommendation)
```

### Run tests

```bash
pytest ../tests/test_dataset_analyzer.py -v
```

---

## GPU Recommender

Estimates VRAM for your model, ranks GPUs from the hardware database, and suggests cloud providers.

### How it works

1. **Input** — Model size (billions), batch size, precision, training mode, model type.
2. **VRAM estimate** — `params × bytes-per-param + activation memory + overhead`.
3. **GPU database** — Loads specs from `knowledge/hardware/gpus.yaml` (VRAM, TFLOPS, power, tier).
4. **Scoring** — Filters by VRAM fit, ranks by utilization, speed, budget, vendor.
5. **Cloud match** — Maps top GPUs to AWS, GCP, RunPod, Lambda, etc. from `knowledge/hardware/cloud.yaml`.
6. **Rule engine** — Fires hardware rules (multi-GPU, ROCm compatibility, etc.).
7. **Output** — Ranked GPUs, best pick, cloud options, warnings, recommendations.

### CLI usage

```bash
# 7B model, LoRA fine-tuning
trainwise recommend-gpu --params-billion 7 --mode lora --type transformer

# Small vision model, mid budget
trainwise recommend-gpu --params-billion 0.1 --type vision --budget mid

# Large full fine-tune (datacenter GPUs)
trainwise recommend-gpu --params-billion 13 --mode full --type transformer

# AMD only, JSON output
trainwise recommend-gpu -p 1 --vendor amd --format json
```

### CLI flags

| Flag | Values | Default |
|------|--------|---------|
| `--params-billion` / `-p` | Model size in billions | required |
| `--batch-size` / `-b` | Batch size | 8 |
| `--mode` / `-m` | `full`, `lora`, `inference` | full |
| `--type` / `-t` | `vision`, `cnn`, `transformer` | vision |
| `--precision` | `fp32`, `fp16`, `int8` | fp16 |
| `--budget` | `entry`, `mid`, `high`, `enthusiast`, `datacenter` | — |
| `--vendor` | `nvidia`, `amd` | — |
| `--no-cloud` | Skip cloud suggestions | false |

### Python API

```python
from app.core.recommenders.gpu import GPURecommender, GPURecommendationRequest, TrainingMode
from app.core.recommenders.gpu.models import ModelType

request = GPURecommendationRequest(
    parameter_count_billion=7.0,
    training_mode=TrainingMode.LORA,
    model_type=ModelType.TRANSFORMER,
    batch_size=4,
)
result = GPURecommender().recommend(request)
print(f"VRAM needed: {result.required_vram_gb} GB")
print(f"Best pick: {result.best_pick.gpu.name}")
```

### Run tests

```bash
pytest ../tests/test_gpu_recommender.py -v
```

---

## Knowledge Engine

Rules live in `knowledge/` as YAML files. The engine:

1. Auto-loads all YAML from `knowledge/`
2. Evaluates conditions against runtime context
3. Scores and ranks recommendations
4. Resolves conflicts by category
5. Returns recommendations, warnings, confidence, and sources

## Plugin System

The engine is pluggable. The default `rule-based` plugin wraps the YAML knowledge engine.
An LLM-based plugin can be added later without changing API or CLI interfaces.

## License

MIT
