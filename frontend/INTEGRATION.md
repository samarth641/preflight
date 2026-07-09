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

### Integrated (ready to connect)

| Frontend Function | Backend Endpoint | Notes |
|------------------|------------------|-------|
| `getHealth()` | `GET /api/v1/health` | Direct match |
| `analyzeDataset()` | `POST /api/v1/dataset/analyze` | Backend takes `{ path, max_images }`. Manual entry mode (metrics only) doesn't have a backend endpoint yet. |
| `recommendGPU()` | `POST /api/v1/gpu/recommend` | Backend now returns `cost_estimate` per candidate and `cheapest_gpu`. `lib/types.ts` needs those fields added. New request fields (`include_cost`, `epochs`, `dataset_samples`, `deployment`) not sent yet. |
| `getTrainingHealth()` | `POST /api/v1/training/analyze` | Backend takes `{ path }` to a log file. Frontend "live monitoring" is ahead of this — WebSocket streaming is future. |
| `estimateCost()` | `POST /api/v1/cost/estimate` | Not wired into the UI yet. Can add to GPU or Analyze page. |

### Not integrated (no backend endpoint yet)

| Frontend Page | Suggested Endpoint |
|---------------|-------------------|
| Dashboard stats | `GET /api/v1/dashboard/stats` |
| Pre-Training predictions (cost, runtime, OOM, convergence, accuracy) | `POST /api/v1/predict` |
| AI Explanation | `POST /api/v1/explain` |
| Experiment history | `GET/DELETE /api/v1/experiments` |
| Live training stream | `WS /api/v1/training/:id/stream` |

Frontend works with mock data until each endpoint is ready. Connect one at a time.

## Type Sync

Backend models changed since `lib/types.ts` was written. New fields to add:

- `GPUCandidate.cost_estimate: CostEstimateResult | None`
- `GPURecommendationResult.cheapest_gpu: GPUCandidate | None`
- `GPURecommendationRequest`: `include_cost`, `epochs`, `dataset_samples`, `dataset_size_gb`, `deployment`

Just let me know when models change and I'll update the types.

## Error Handling

Backend returns `{ "detail": "..." }` on errors. Frontend currently shows a generic message — can parse `error.detail` later for better UX. Low priority.
