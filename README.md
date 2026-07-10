# Preflight

AI Training Intelligence Platform — a rule-based expert system for ML training recommendations.

## Status

**Phase 1 complete:** Foundation architecture, knowledge engine, rule loader, and plugin system.

**Phase 2 complete:** Dataset Analyzer, GPU Recommender, Training Log Analyzer.

## Quick Start

```bash
cd backend
pip install -e ".[dev]"
trainwise doctor
trainwise analyze-dataset /path/to/your/dataset
trainwise recommend-gpu --params-billion 7 --mode lora --type transformer
trainwise estimate-cost --params-billion 7 --gpu rtx-4090 --epochs 10
trainwise analyze-training /path/to/training_log.csv
uvicorn app.main:app --reload --port 8000
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
**API docs:** [docs/api.md](docs/api.md) — REST endpoints + curl examples.

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

## Cost Calculator

Estimates training time and cost (cloud, electricity, storage, bandwidth). **Integrated into GPU Recommender** — each ranked GPU includes a `cost_estimate`.

### CLI

```bash
trainwise estimate-cost --params-billion 7 --gpu rtx-4090 --epochs 10 --provider runpod
trainwise recommend-gpu -p 7 --mode lora --epochs 10   # includes cost per GPU
```

### Python API

```python
from app.core.calculators import CostCalculator, CostEstimateRequest
from app.core.calculators.cost.models import DeploymentType

result = CostCalculator().estimate(CostEstimateRequest(
    parameter_count_billion=7.0,
    gpu_id="rtx-4090",
    epochs=10,
    deployment=DeploymentType.CLOUD,
    cloud_provider="runpod",
))
print(f"${result.total_usd:.2f} — {result.estimated_hours:.1f} hours")
```

Pricing: `knowledge/hardware/pricing.yaml`

---

## REST API

```bash
uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000/docs
```

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/dataset/analyze` | Dataset quality analysis |
| `POST /api/v1/training/analyze` | Training log health |
| `POST /api/v1/gpu/recommend` | GPU ranking + cost |
| `POST /api/v1/cost/estimate` | Standalone cost estimate |
| `POST /api/v1/predict/duration` | **ML** training duration + cost prediction |
| `POST /api/v1/explain` | **AI** plain-language explanation of a rule-engine result |

Full reference: [docs/api.md](docs/api.md)

---

## Training Log Analyzer

Reads a training log (CSV/JSON), detects health issues (overfitting, stagnation, bottlenecks), scores
training health, and returns rule-based recommendations. It is **not** an AI model — every
recommendation comes from the YAML knowledge engine.

### How it works

1. **Parse** — Reads CSV or JSON logs with flexible column aliases (`loss`/`train_loss`, `acc`/`accuracy`, etc.).
2. **Trend detection** — Computes signals: validation loss increasing, overfitting gap, loss stagnation,
   divergence, accuracy plateau, low GPU/CPU utilization, VRAM near limit.
3. **Score (0–100)** — Starts at 100, subtracts for each detected issue → grade A–F.
4. **Rule engine** — Signals sent to `knowledge/pytorch/training.yaml` and `knowledge/training/health.yaml`
   (categories `training`, `optimization`) → warnings + recommendations.
5. **Output** — Score, metrics, trends, warnings, recommendations, sources.

### CLI usage

```bash
trainwise analyze-training training_log.csv
trainwise analyze-training wandb_export.json --format json
trainwise analyze-training training_log.csv --format markdown
```

### Expected CSV format

```csv
epoch,train_loss,val_loss,accuracy,gpu_util,cpu_util,vram_gb,power_w
1,2.31,2.45,0.42,85,30,8.2,220
2,1.89,2.10,0.55,88,32,8.4,230
```

JSON logs use `{"epochs": [{"epoch": 1, "train_loss": 2.31, "val_loss": 2.45}, ...]}` or a plain list.

### Python API

```python
from app.core.analyzers import TrainingAnalyzer

result = TrainingAnalyzer().analyze("training_log.csv")
print(f"Health: {result.score}/100 ({result.grade})")
print(f"Overfitting: {result.metrics.overfitting_detected}")
for rec in result.recommendations:
    print(f"  → {rec.recommendation} ({rec.source})")
```

### Run tests

```bash
pytest ../tests/test_training_analyzer.py -v
```

---

## Duration Predictor (ML — Phase 3)

XGBoost regression predicting training duration **before execution**, trained on
414 real training runs (Epoch AI, label-filtered) + 430 physics-derived synthetic
rows covering AMD (MI300X, RX 7900 XTX) and consumer GPUs. Cost = predicted
hours × GPU hourly rate.

Evaluation (grouped-by-organization split, corrupt labels filtered — see
`artifacts/metrics.json`): the ML model and the analytical formula are
complementary. On the matched held-out subset (real rows with the full physics
feature), the formula wins on typical cases (median 1.17x vs 1.52x) while the
ML model wins on the tail (p90 2.52x vs 3.29x). Both numbers are returned by
the API so users see estimate + physics floor.

**Caveat:** p90 is unstable across the grouped split at this sample size (~84
matched test rows) — it moved from 9.8x/5.6x to 3.29x/2.52x between two runs
on different grouped splits of the same data. Treat p90 as directional, not
a precise bound, until the dataset grows.

### CLI

```bash
trainwise predict-duration -p 7 -d 100e9 -g mi300x -n 4 --provider aws
trainwise predict-duration -p 1 -d 2e9 -g rtx-4090 --format json
```

### Retraining

```bash
python ml/prep_dataset.py --augment   # data/raw/* -> data/processed/duration_train.csv
python ml/train_duration.py           # -> backend/app/core/predictors/duration/artifacts/
```

Artifact is a ~300 KB JSON loaded at startup — no model server needed.

---

## AI Explanation Engine (Gemma, fine-tuned on AMD ROCm)

**Status: live and verified end-to-end.** The fine-tuned model is trained, converted to GGUF,
and serving — `trainwise analyze-training <log> --explain` returns `backend: "gemma-finetuned"`,
confirming the model (not the fallback) is answering.

Turns a rule-engine result (matched recommendations + warnings) into a plain-language
explanation: an opening sentence, a "because:" bullet list, a "Recommended actions:"
checklist, and an "Estimated impact:" line — the format the Core Objectives doc specifies.

Training data is generated straight from `knowledge/*.yaml` (`ml/generate_explanation_dataset.py`,
reuses the real `RuleLoader` — no hand-written gold data, no drift). Fine-tuned with LoRA
(Unsloth) on an AMD GPU via ROCm (`ml/finetune_gemma_explainer_amd.py`), then merged and exported
to GGUF for `llama-cpp-python` serving; see
[docs/explanation-engine-handoff.md](docs/explanation-engine-handoff.md) for the run steps and
[docs/gguf-conversion-and-serving.md](docs/gguf-conversion-and-serving.md) for the conversion/serving path.

**Always demoable:** if the fine-tuned `.gguf` artifact isn't present, `ExplanationEngine` falls
back to a deterministic template in the same house style — same graceful-degradation pattern as
the duration predictor. Check the `backend` field in the response (`"template"` vs
`"gemma-finetuned"`) to see which one answered.

**On the roadmap (actively improving):** a quantized Q4_K_M build is in the pipeline for faster
inference, alongside broader explanation coverage across more rule combinations — both in progress
to make the engine leaner and more general.

### CLI

```bash
trainwise analyze-training training_log.csv --explain
```

### API

```bash
curl -X POST http://localhost:8000/api/v1/explain \
  -H "Content-Type: application/json" \
  -d '{"engine_result": {"recommendations": [...], "warnings": [...]}, "context": {}}'
```

### Run tests

```bash
pytest ../tests/test_explainer.py -v
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
