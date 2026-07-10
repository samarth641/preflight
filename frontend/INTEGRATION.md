# Backend Integration

Frontend connects to the Preflight FastAPI backend via `lib/api.ts`.

## Setup

**Terminal 1 — API:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Environment

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1
# NEXT_PUBLIC_USE_MOCK=true   # force mock mode (no backend)
```

## Endpoint Status

### Connected to backend

| Frontend | Backend |
|----------|---------|
| `getHealth()` | `GET /health` |
| `getDashboardStats()` | `GET /dashboard/stats` |
| `listExperiments()` | `GET /experiments` |
| `getLiveMonitor()` | `GET /training/monitor` |
| `getRecentActivity()` | derived from `/experiments` |
| `recommendGPU()` | `POST /gpu/recommend` |
| `estimateCost()` | `POST /cost/estimate` |
| `predictDuration()` | `POST /predict/duration` |
| `analyzeDataset({ path })` | `POST /dataset/analyze` |
| `getTrainingHealth(demo job)` | `GET /training/monitor` (demo → exp-live-100m) |
| `getTrainingMetrics(demo job)` | curve from `/training/monitor` |
| `analyzeTraining()` | composed from GPU + duration + cost APIs |

### Still mock / client-side

| Frontend | Reason |
|----------|--------|
| `analyzeDataset(manual metrics)` | No backend endpoint for manual entry |
| `listGPUBenchmarks()` | No dedicated API (embedded in knowledge YAML) |
| `startTraining()` / `stopTraining()` | Demo controls only |
| `exportAnalysis()` | No backend export endpoint |
| Pre-training `oom_probability`, `carbon_footprint_kg`, etc. | Heuristic estimates — labeled in UI |

## Dataset path mode

`analyzeDataset({ path })` requires a path the **backend server** can read (local dev: absolute path like `F:/PREFLIIGHT/tests/_cli_sample`).

## Demo training job

The training page demo job `demo-vit-base-live` maps to experiment `exp-live-100m` and uses rule-based monitor fixtures in `tests/fixtures/experiments/`.
