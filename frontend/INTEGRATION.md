# Backend Integration

Frontend runs on mock data right now. Swapping to real API is a single-file change — only `lib/api.ts` changes. Everything else stays the same.

---

## CORS

Add to `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Env Var

Create `.env.local` in `frontend/`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Swapping Mock for Real

In `lib/api.ts`, each function currently returns mock data. Replace with a real fetch call:

```typescript
export async function recommendGPU(req: GPURecommendationRequest): Promise<GPURecommendationResult> {
  const res = await fetch(`${API_URL}/gpu/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(`GPU recommend failed: ${res.status}`)
  return res.json()
}
```

Signatures and return types stay identical — components don't change.

## Endpoint Status

### Ready to connect (8 endpoints)

| Frontend Function | Backend Endpoint | Notes |
|------------------|------------------|-------|
| `getHealth()` | `GET /api/v1/health` | Direct match |
| `analyzeDataset(input)` | `POST /api/v1/dataset/analyze` | Backend takes `{ path, max_images }`. Manual entry mode (metrics only) has no endpoint yet. |
| `recommendGPU(req)` | `POST /api/v1/gpu/recommend` | Types match. Returns `cost_estimate` per candidate, `cheapest_gpu`. |
| `predictDuration(req)` | `POST /api/v1/predict/duration` | XGBoost model. Returns estimated hours + optional cost. |
| `estimateCost(req)` | `POST /api/v1/cost/estimate` | Cloud/electricity breakdown, multi-GPU scaling. |
| `getTrainingHealth(jobId)` | `POST /api/v1/training/analyze` | Backend takes `{ path }` to a log file. |
| `getDashboardStats()` | `GET /api/v1/dashboard/stats` | Returns experiment stats: total, running, completed, failed, avg_accuracy, convergence_rate. |
| `listExperiments()` | `GET /api/v1/experiments` | Returns `ExperimentRecord[]` with params_million, epochs, convergence, duration. |
| `getLiveMonitor(id?)` | `GET /api/v1/training/monitor` | Returns `LiveTrainingMonitor` with epoch curve, convergence status, health score. |

### No backend endpoint (stay mock or remove)

| Frontend Function | Issue | Action |
|------------------|-------|--------|
| `analyzeTraining(req)` | No `/analyze` endpoint. PredictionResult fields are fabricated | Remove fabricated fields. Use `predictDuration()` + `estimateCost()` instead. |
| `getRecentActivity()` | No endpoint | Derive from experiment list or keep mock |
| `startTraining()` / `stopTraining()` | No endpoint | Keep mock |
| `exportAnalysis()` | No endpoint | Keep mock |
| `listGPUs()` / `listGPUBenchmarks()` / `listCloudOfferings()` | No dedicated endpoint | Add to backend or embed |

## Fabricated Fields (no backend support)

The `/analyze` page has a PLACEHOLDER section with fields that have NO backend implementation:
- `oom_probability`, `convergence_probability`, `expected_accuracy_min/max`
- `gpu_utilization_estimate`, `carbon_footprint_kg`, `bottlenecks`

These are marked as PLACEHOLDER in `types.ts` and `mock-data.ts`. They should be removed or labeled as "Roadmap" for the demo.

## Error Handling

Backend returns `{ "detail": "..." }` on errors. Frontend currently shows a generic message — can parse `error.detail` later for better UX. Low priority.
