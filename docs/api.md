# Preflight REST API

The Preflight API exposes the same business logic as the `trainwise` CLI. All endpoints are under `/api/v1`.

**Interactive docs:** run the server and open [http://localhost:8000/docs](http://localhost:8000/docs)

## Quick start

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Root health check |
| `GET` | `/api/v1/health` | API health + version |
| `POST` | `/api/v1/dataset/analyze` | Analyze image dataset quality |
| `POST` | `/api/v1/training/analyze` | Analyze training log health |
| `POST` | `/api/v1/gpu/recommend` | Recommend GPUs + cost estimates |
| `POST` | `/api/v1/cost/estimate` | Estimate training cost |

---

## POST `/api/v1/dataset/analyze`

Scan an image dataset directory and return quality score, metrics, and recommendations.

### Request

```json
{
  "path": "F:/datasets/my_dataset",
  "max_images": 1000
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `path` | string | yes | Path to dataset folder (class-folder layout) |
| `max_images` | int | no | Limit images scanned |

### Response (summary)

```json
{
  "score": 85.0,
  "grade": "B",
  "metrics": { "image_count": 300, "class_imbalance_ratio": 1.2, ... },
  "recommendations": [...],
  "accuracy_impact": { "estimated_loss_percent": 2.0, ... }
}
```

### Errors

| Status | Cause |
|--------|-------|
| `404` | Dataset path not found |
| `400` | Invalid path (not a directory) |

### Example

```bash
curl -X POST http://localhost:8000/api/v1/dataset/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "F:/PREFLIIGHT/tests/fixtures/training/../_cli_sample"}'
```

---

## POST `/api/v1/training/analyze`

Analyze a training log CSV or JSON file for overfitting, stagnation, and bottlenecks.

### Request

```json
{
  "path": "F:/logs/training_log.csv"
}
```

### Response (summary)

```json
{
  "score": 65.0,
  "grade": "D",
  "metrics": {
    "validation_loss_increasing": true,
    "overfitting_detected": true,
    ...
  },
  "trends": [...],
  "recommendations": [...]
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/v1/training/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "F:/PREFLIIGHT/tests/fixtures/training/overfitting.csv"}'
```

---

## POST `/api/v1/gpu/recommend`

Estimate VRAM, rank GPUs, attach **cost estimates**, and suggest cloud providers.

### Request

```json
{
  "parameter_count_billion": 7.0,
  "training_mode": "lora",
  "model_type": "transformer",
  "batch_size": 8,
  "epochs": 10,
  "dataset_samples": 10000,
  "include_cost": true,
  "deployment": "cloud",
  "max_results": 5
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `parameter_count_billion` | float | required | Model size in billions |
| `training_mode` | string | `full` | `full`, `lora`, `inference` |
| `model_type` | string | `vision` | `vision`, `cnn`, `transformer` |
| `batch_size` | int | 8 | Training batch size |
| `epochs` | int | 10 | Epochs for cost estimate |
| `dataset_samples` | int | 10000 | Dataset size for cost/time |
| `include_cost` | bool | true | Attach cost per GPU candidate |
| `deployment` | string | `cloud` | `cloud` or `local` |
| `preferred_vendor` | string | — | `nvidia` or `amd` |
| `budget_tier` | string | — | `entry`, `mid`, `high`, `enthusiast`, `datacenter` |

### Response (summary)

```json
{
  "required_vram_gb": 18.55,
  "best_pick": { "gpu": { "name": "NVIDIA RTX 4090", ... }, "cost_estimate": { "total_usd": 12.5, ... } },
  "cheapest_gpu": { ... },
  "candidates": [
    {
      "gpu": { "id": "rtx-4090", "name": "NVIDIA RTX 4090", ... },
      "score": 0.66,
      "fit_rating": "excellent",
      "cost_estimate": {
        "total_usd": 12.50,
        "estimated_hours": 28.4,
        "breakdown": { "cloud_usd": 12.50, "electricity_usd": 0, ... }
      }
    }
  ],
  "cloud_offerings": [...],
  "knowledge_recommendations": [...]
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/v1/gpu/recommend \
  -H "Content-Type: application/json" \
  -d '{"parameter_count_billion": 7, "training_mode": "lora", "model_type": "transformer"}'
```

---

## POST `/api/v1/cost/estimate`

Standalone cost estimate for a specific GPU and workload.

### Request

```json
{
  "parameter_count_billion": 7.0,
  "gpu_id": "rtx-4090",
  "epochs": 10,
  "dataset_samples": 10000,
  "batch_size": 8,
  "model_type": "transformer",
  "deployment": "cloud",
  "cloud_provider": "runpod"
}
```

### Response

```json
{
  "gpu_id": "rtx-4090",
  "gpu_name": "NVIDIA RTX 4090",
  "deployment": "cloud",
  "estimated_hours": 28.4,
  "estimated_days": 1.18,
  "seconds_per_epoch": 10224.0,
  "hourly_rate_usd": 0.44,
  "total_usd": 12.50,
  "breakdown": {
    "cloud_usd": 12.50,
    "electricity_usd": 0.0,
    "storage_usd": 0.12,
    "bandwidth_usd": 0.45,
    "hardware_amortization_usd": 0.0
  },
  "notes": []
}
```

### Cost components

| Component | Cloud | Local |
|-----------|-------|-------|
| **Cloud compute** | `hourly_rate × hours` | $0 |
| **Electricity** | fallback if no cloud rate | `kW × hours × $/kWh` |
| **Storage** | dataset GB × monthly rate | same |
| **Bandwidth** | dataset upload cost | $0 |
| **Hardware amortization** | $0 | MSRP / lifetime hours × hours |

Pricing lives in `knowledge/hardware/pricing.yaml` (not hardcoded).

### Example

```bash
curl -X POST http://localhost:8000/api/v1/cost/estimate \
  -H "Content-Type: application/json" \
  -d '{"parameter_count_billion": 7, "gpu_id": "rtx-4090", "epochs": 10, "cloud_provider": "runpod"}'
```

---

## CLI equivalents

| API | CLI |
|-----|-----|
| `POST /dataset/analyze` | `trainwise analyze-dataset PATH` |
| `POST /training/analyze` | `trainwise analyze-training PATH` |
| `POST /gpu/recommend` | `trainwise recommend-gpu -p 7 --mode lora` |
| `POST /cost/estimate` | `trainwise estimate-cost -p 7 -g rtx-4090` |

---

## Architecture

```
Client (curl / frontend / CLI)
        │
        ▼
  FastAPI /api/v1/*
        │
        ├── DatasetAnalyzer
        ├── TrainingAnalyzer
        ├── GPURecommender ──► CostCalculator (integrated)
        └── CostCalculator
                │
                ▼
        KnowledgeEngine (YAML rules)
```

Business logic lives in `app/core/` — the API layer only validates input and calls the same classes the CLI uses.

---

## Testing

```bash
cd backend
pytest ../tests/test_api.py -v
pytest ../tests/test_cost_calculator.py -v
pytest ../tests -v
```

---

## Error format

FastAPI returns standard HTTP errors:

```json
{
  "detail": "Dataset path not found: /bad/path"
}
```

---

## Next steps (future)

- Authentication / API keys
- File upload endpoints (instead of server-side paths)
- WebSocket streaming for live training log analysis
- OpenAPI client generation for the Next.js dashboard
