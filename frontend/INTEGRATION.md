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
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

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

### Ready to connect (5 endpoints — verified in routes.py)

| Frontend Function | Backend Endpoint | Notes |
|------------------|------------------|-------|
| `getHealth()` | `GET /api/v1/health` | Direct match |
| `analyzeDataset({ path })` | `POST /api/v1/dataset/analyze` | Backend takes `{ path, max_images }`. Manual entry mode (metrics only) has no endpoint — keep mock or add backend support. |
| `recommendGPU(req)` | `POST /api/v1/gpu/recommend` | Types match. `GPURecommendBody` schema matches `GPURecommendationRequest` in types.ts. |
| `estimateCost(req)` | `POST /api/v1/cost/estimate` | Types match. `CostEstimateBody` schema matches `CostEstimateRequest`. |
| `getTrainingHealth(jobId)` | `POST /api/v1/training/analyze` | Backend takes `{ path }` to a log file. Frontend passes `jobId` — needs adaptation. |

### No backend endpoint (stay mock)

| Frontend Function | Issue | Action |
|------------------|-------|--------|
| `predictDuration(req)` | No `/predict/duration` endpoint in routes.py | XGBoost model exists in CLI but no API route. Add endpoint or keep mock. |
| `getDashboardStats()` | No `/dashboard/stats` endpoint | Keep mock or add endpoint |
| `listExperiments()` | No `/experiments` endpoint | Keep mock or add endpoint |
| `getLiveMonitor(id?)` | No `/training/monitor` endpoint | Keep mock or add endpoint |
| `getRecentActivity()` | No endpoint | Derive from experiment list or keep mock |
| `analyzeTraining(req)` | No `/analyze` endpoint | Fabricated PredictionResult fields. Use `predictDuration()` + `estimateCost()` instead. |
| `startTraining()` / `stopTraining()` | No endpoint | Frontend-only controls, keep mock |
| `getTrainingMetrics()` | No endpoint | Keep mock |
| `exportAnalysis()` | No endpoint | Keep mock |
| `listGPUs()` / `listGPUBenchmarks()` / `listCloudOfferings()` | No dedicated endpoint | Add to backend or embed in GPU response |

### Known type mismatch

- `CostEstimateResult` in frontend types has `gpu_hours` field that the backend `CostEstimateResult` Pydantic model does not include. When swapping to real fetch, this field will be `undefined`. The cost page reads it for display — either add it to the backend model or handle the missing field in the page.

## Fabricated Fields (no backend support)

The pre-training page has fields with NO backend implementation:
- `oom_probability`, `convergence_probability`, `expected_accuracy_min/max`
- `gpu_utilization_estimate`, `carbon_footprint_kg`, `bottlenecks`

These are clearly labeled in the page as estimates. They should be removed or labeled as "Roadmap" for production.

## Error Handling

Backend returns `{ "detail": "..." }` on errors. Frontend currently shows a generic message — can parse `error.detail` later for better UX. Low priority.
